# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivLibraryFineRule(models.Model):
    _name = "univ.library.fine.rule"
    _description = "Library Fine Rule"
    _order = "name"

    name = fields.Char(string="Rule", required=True)
    per_day = fields.Float(string="Fine per Day", default=1.0)
    grace_days = fields.Integer(string="Grace Days", default=0)
    max_amount = fields.Float(string="Maximum Fine", default=0.0,
                              help="0 means no cap.")
    lost_charge = fields.Float(string="Lost Book Charge", default=0.0)
    fee_head_id = fields.Many2one(
        comodel_name="univ.fee.head", string="Fee Head",
        help="Fee head used when posting fines to the student ledger.")
    is_default = fields.Boolean(string="Default")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    @api.model
    def _get_default(self):
        rule = self.search([("is_default", "=", True)], limit=1)
        if not rule:
            rule = self.search([], limit=1)
        return rule


class UnivLibraryFine(models.Model):
    _name = "univ.library.fine"
    _description = "Library Fine"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    issue_id = fields.Many2one(comodel_name="univ.library.issue",
                               string="Issue", required=True, ondelete="cascade",
                               index=True)
    member_id = fields.Many2one(comodel_name="univ.library.member",
                                string="Member", required=True, index=True)
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 related="member_id.student_id", store=True)
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id)
    fee_invoice_id = fields.Many2one(comodel_name="univ.fee.invoice",
                                     string="Fee Invoice", readonly=True)
    state = fields.Selection(
        selection=[("draft", "Draft"), ("posted", "Posted to Fees"),
                   ("cancelled", "Cancelled")],
        string="Status", default="draft", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    def action_post_to_fee(self):
        """Post this fine to the student fee ledger via the fee bridge."""
        for fine in self:
            if fine.state == "posted" and fine.fee_invoice_id:
                continue
            student = fine.student_id
            if not student:
                # Faculty fines are tracked but not routed to the student ledger.
                fine.state = "posted"
                continue
            rule = self.env["univ.library.fine.rule"]._get_default()
            head = rule.fee_head_id if rule else False
            if not head:
                raise UserError(_(
                    "Configure a Fee Head on the library fine rule first."))
            invoice = self.env["univ.fee.invoice"].create_service_charge(
                student, head, fine.amount,
                label=_("Library fine: %s", fine.issue_id.book_id.name),
            )
            fine.write({"state": "posted", "fee_invoice_id": invoice.id})

    def action_cancel(self):
        self.write({"state": "cancelled"})
