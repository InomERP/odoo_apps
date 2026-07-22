# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UnivHostelAllotment(models.Model):
    _name = "univ.hostel.allotment"
    _description = "Hostel Allotment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", copy=False, readonly=True,
                       default=lambda self: _("New"))
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True, index=True, tracking=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel",
                                required=True, index=True)
    bed_id = fields.Many2one(comodel_name="univ.hostel.bed", string="Bed",
                             tracking=True)
    room_id = fields.Many2one(comodel_name="univ.hostel.room", string="Room",
                              related="bed_id.room_id", store=True)
    apply_date = fields.Date(string="Applied On",
                             default=fields.Date.context_today)
    checkin_date = fields.Date(string="Check-in")
    checkout_date = fields.Date(string="Check-out")
    deposit_amount = fields.Monetary(string="Security Deposit")
    hostel_fee = fields.Monetary(string="Hostel Fee")
    deposit_settled = fields.Boolean(string="Deposit Settled", readonly=True)
    fee_invoice_id = fields.Many2one(comodel_name="univ.fee.invoice",
                                     string="Fee Invoice", readonly=True)
    fee_head_id = fields.Many2one(comodel_name="univ.fee.head",
                                  string="Hostel Fee Head")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id)
    state = fields.Selection(
        selection=[
            ("applied", "Applied"),
            ("allotted", "Allotted"),
            ("checked_in", "Checked In"),
            ("checkout_req", "Checkout Requested"),
            ("settled", "Deposit Settled"),
            ("cancelled", "Cancelled"),
        ], string="Status", default="applied", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (_("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.hostel.allotment") or "HST-A/0001"
        return super().create(vals_list)

    @api.constrains("bed_id", "state")
    def _check_bed_capacity(self):
        for rec in self.filtered(lambda r: r.bed_id and r.state in (
                "allotted", "checked_in")):
            other = self.search_count([
                ("id", "!=", rec.id), ("bed_id", "=", rec.bed_id.id),
                ("state", "in", ("allotted", "checked_in"))])
            if other:
                raise ValidationError(_(
                    "Bed %s is already allotted.", rec.bed_id.display_name))

    def action_allot(self):
        """Allot the bed, inject the hostel fee head, post deposit + fee."""
        for rec in self:
            if not rec.bed_id:
                raise UserError(_("Select a bed to allot."))
            if rec.bed_id.state != "available":
                raise UserError(_("Selected bed is not available."))
            rec.bed_id.state = "occupied"
            rec.state = "allotted"
            rec._post_fee()

    def _post_fee(self):
        self.ensure_one()
        if self.fee_invoice_id:
            return
        total = (self.deposit_amount or 0.0) + (self.hostel_fee or 0.0)
        if total <= 0:
            return
        head = self.fee_head_id
        if not head:
            raise UserError(_(
                "Set a Hostel Fee Head before allotment."))
        invoice = self.env["univ.fee.invoice"].create_service_charge(
            self.student_id, head, total,
            label=_("Hostel allotment: %s", self.hostel_id.name))
        self.fee_invoice_id = invoice.id

    def action_check_in(self):
        for rec in self:
            if rec.state != "allotted":
                raise UserError(_("Allot the bed first."))
            rec.write({"state": "checked_in",
                       "checkin_date": fields.Date.context_today(rec)})

    def action_request_checkout(self):
        self.write({"state": "checkout_req"})

    def action_settle_deposit(self):
        """Free the bed and mark the security deposit as settled."""
        for rec in self:
            if rec.state != "checkout_req":
                raise UserError(_("Checkout must be requested first."))
            if rec.bed_id:
                rec.bed_id.state = "available"
            rec.write({
                "state": "settled",
                "deposit_settled": True,
                "checkout_date": fields.Date.context_today(rec),
            })

    def action_cancel(self):
        for rec in self:
            if rec.bed_id and rec.bed_id.state == "occupied":
                rec.bed_id.state = "available"
            rec.state = "cancelled"


class UnivHostelTransfer(models.Model):
    _name = "univ.hostel.transfer"
    _description = "Hostel Transfer"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    allotment_id = fields.Many2one(comodel_name="univ.hostel.allotment",
                                   string="Allotment", required=True, index=True)
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 related="allotment_id.student_id", store=True)
    current_bed_id = fields.Many2one(comodel_name="univ.hostel.bed",
                                     string="Current Bed",
                                     related="allotment_id.bed_id")
    new_bed_id = fields.Many2one(comodel_name="univ.hostel.bed", string="New Bed",
                                 required=True)
    reason = fields.Text(string="Reason")
    state = fields.Selection(
        selection=[("draft", "Draft"), ("approved", "Approved"),
                   ("done", "Transferred")],
        string="Status", default="draft", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="allotment_id.company_id", store=True, index=True)

    def action_approve(self):
        self.write({"state": "approved"})

    def action_transfer(self):
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("Approve the transfer first."))
            if rec.new_bed_id.state != "available":
                raise UserError(_("New bed is not available."))
            if rec.current_bed_id:
                rec.current_bed_id.state = "available"
            rec.new_bed_id.state = "occupied"
            rec.allotment_id.bed_id = rec.new_bed_id.id
            rec.state = "done"
