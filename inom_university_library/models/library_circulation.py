# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class UnivLibraryReservation(models.Model):
    _name = "univ.library.reservation"
    _description = "Book Reservation"
    _inherit = ["mail.thread"]
    _order = "reserve_date desc, id desc"

    book_id = fields.Many2one(comodel_name="univ.library.book", string="Book",
                              required=True, index=True)
    member_id = fields.Many2one(comodel_name="univ.library.member",
                                string="Member", required=True, index=True)
    reserve_date = fields.Date(string="Reserved On",
                               default=fields.Date.context_today)
    state = fields.Selection(
        selection=[("pending", "Pending"), ("fulfilled", "Fulfilled"),
                   ("cancelled", "Cancelled"), ("expired", "Expired")],
        string="Status", default="pending", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="book_id.company_id", store=True, index=True)

    def action_fulfil(self):
        self.write({"state": "fulfilled"})

    def action_cancel(self):
        self.write({"state": "cancelled"})


class UnivLibraryIssue(models.Model):
    _name = "univ.library.issue"
    _description = "Book Issue"
    _inherit = ["mail.thread"]
    _order = "issue_date desc, id desc"

    name = fields.Char(string="Reference", copy=False, readonly=True,
                       default=lambda self: self.env._("New"))
    copy_id = fields.Many2one(comodel_name="univ.library.copy", string="Copy",
                              required=True, index=True)
    book_id = fields.Many2one(comodel_name="univ.library.book", string="Book",
                              related="copy_id.book_id", store=True, index=True)
    member_id = fields.Many2one(comodel_name="univ.library.member",
                                string="Member", required=True, index=True)
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 related="member_id.student_id", store=True)
    issue_date = fields.Date(string="Issued On",
                             default=fields.Date.context_today, required=True)
    due_date = fields.Date(string="Due On", required=True)
    return_date = fields.Date(string="Returned On")
    renew_count = fields.Integer(string="Renewals", default=0)
    state = fields.Selection(
        selection=[
            ("issued", "Issued"),
            ("overdue", "Overdue"),
            ("returned", "Returned"),
            ("lost", "Lost"),
        ], string="Status", default="issued", required=True, tracking=True,
        index=True)
    fine_ids = fields.One2many(comodel_name="univ.library.fine",
                               inverse_name="issue_id", string="Fines")
    fine_total = fields.Monetary(string="Fine", compute="_compute_fine",
                                 store=True)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    @api.depends("fine_ids.amount", "fine_ids.state")
    def _compute_fine(self):
        for issue in self:
            issue.fine_total = sum(issue.fine_ids.filtered(
                lambda f: f.state != "cancelled").mapped("amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (self.env._("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.library.issue") or "LIB-I/0001"
            if not vals.get("due_date") and vals.get("issue_date"):
                vals["due_date"] = fields.Date.from_string(
                    vals["issue_date"]) + timedelta(days=14)
        issues = super().create(vals_list)
        issues.mapped("copy_id").write({"state": "issued"})
        return issues

    @api.constrains("member_id", "state")
    def _check_limit(self):
        for issue in self.filtered(lambda i: i.state in ("issued", "overdue")):
            member = issue.member_id
            if member.state != "active":
                raise ValidationError(self.env._(
                    "Member card is not active."))
            count = self.search_count([
                ("member_id", "=", member.id),
                ("state", "in", ("issued", "overdue"))])
            if count > member.max_books:
                raise ValidationError(self.env._(
                    "Book limit (%s) exceeded for %s.",
                    member.max_books, member.name))

    def action_renew(self):
        for issue in self:
            if issue.state not in ("issued", "overdue"):
                raise UserError(self.env._("Only active issues can be renewed."))
            issue.write({
                "due_date": issue.due_date + timedelta(days=14),
                "renew_count": issue.renew_count + 1,
                "state": "issued",
            })

    def action_return(self):
        for issue in self:
            if issue.state == "returned":
                continue
            issue._accrue_fine()
            issue.write({
                "state": "returned",
                "return_date": fields.Date.context_today(issue),
            })
            issue.copy_id.write({"state": "available"})

    def action_mark_lost(self):
        for issue in self:
            issue.copy_id.write({"state": "lost"})
            issue.write({"state": "lost"})
            issue._accrue_fine(lost=True)

    def _accrue_fine(self, lost=False):
        """Compute the overdue (or replacement) fine and post it to the fee
        ledger through the Phase 3 bridge."""
        self.ensure_one()
        rule = self.env["univ.library.fine.rule"]._get_default()
        if not rule:
            return
        today = fields.Date.context_today(self)
        amount = 0.0
        if lost:
            amount = rule.lost_charge
        elif self.due_date and today > self.due_date:
            overdue_days = (today - self.due_date).days - rule.grace_days
            if overdue_days > 0:
                amount = overdue_days * rule.per_day
                if rule.max_amount and amount > rule.max_amount:
                    amount = rule.max_amount
        if amount <= 0:
            return
        existing = self.fine_ids.filtered(lambda f: f.state in ("draft", "posted"))
        if existing:
            existing[0].amount = amount
            fine = existing[0]
        else:
            fine = self.env["univ.library.fine"].create({
                "issue_id": self.id,
                "member_id": self.member_id.id,
                "amount": amount,
            })
        fine.action_post_to_fee()

    @api.model
    def _cron_mark_overdue(self):
        today = fields.Date.context_today(self)
        overdue = self.search([
            ("state", "=", "issued"), ("due_date", "<", today)])
        for issue in overdue:
            issue.state = "overdue"
            issue._accrue_fine()
