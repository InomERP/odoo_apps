# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivFeeWaiver(models.Model):
    _name = "univ.fee.waiver"
    _description = "Fee Waiver / Concession"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Reference", copy=False, readonly=True,
        default=lambda self: _("New"),
    )
    invoice_id = fields.Many2one(
        comodel_name="univ.fee.invoice",
        string="Fee Invoice",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student",
        related="invoice_id.student_id", store=True,
    )
    move_id = fields.Many2one(
        comodel_name="account.move", string="Source Invoice",
        related="invoice_id.move_id",
    )
    waiver_type = fields.Selection(
        selection=[("full", "Full Waiver"), ("partial", "Partial Waiver")],
        string="Waiver Type",
        default="partial",
        required=True,
    )
    amount = fields.Monetary(
        string="Waiver Amount", required=True, currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", string="Currency",
        related="invoice_id.currency_id", store=True,
    )
    reason = fields.Text(string="Reason", required=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("refused", "Refused"),
            ("applied", "Applied"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    credit_note_id = fields.Many2one(
        comodel_name="account.move", string="Credit Note", copy=False,
        readonly=True,
    )
    approver_id = fields.Many2one(
        comodel_name="res.users", string="Approved By", readonly=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="invoice_id.company_id", store=True, index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (_("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.fee.waiver"
                ) or "WVR/0001"
        return super().create(vals_list)

    @api.onchange("waiver_type", "invoice_id")
    def _onchange_waiver_type(self):
        if self.waiver_type == "full" and self.invoice_id:
            self.amount = self.invoice_id.amount_residual or \
                self.invoice_id.amount_total

    @api.constrains("amount")
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise UserError(_("Waiver amount must be positive."))
            if record.invoice_id and record.amount > record.invoice_id.amount_total:
                raise UserError(
                    _("Waiver cannot exceed the invoice total.")
                )

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_review(self):
        self.write({"state": "under_review"})

    def action_approve(self):
        for record in self:
            if record.state not in ("submitted", "under_review"):
                raise UserError(
                    _("Only submitted waivers can be approved.")
                )
            record.approver_id = self.env.user.id
            record.state = "approved"

    def action_refuse(self):
        self.write({"state": "refused"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_apply(self):
        for record in self:
            if record.state != "approved":
                raise UserError(
                    _("Approve the waiver before applying it.")
                )
            if not record.move_id:
                raise UserError(
                    _("The fee invoice has no posted journal entry.")
                )
            record.credit_note_id = record._create_credit_note().id
            record.state = "applied"
            record.message_post(
                body=_(
                    "Waiver credit note %s posted for %s.",
                    record.credit_note_id.name,
                    record.amount,
                )
            )

    def _create_credit_note(self):
        self.ensure_one()
        move = self.move_id
        line_account = False
        for line in move.invoice_line_ids:
            line_account = line.account_id.id
            break
        credit_vals = {
            "move_type": "out_refund",
            "partner_id": move.partner_id.id,
            "invoice_origin": move.name,
            "ref": _("Fee waiver: %s", move.name),
            "journal_id": move.journal_id.id,
            "invoice_line_ids": [
                (0, 0, {
                    "name": _("Fee waiver: %s", self.reason or ""),
                    "quantity": 1.0,
                    "price_unit": self.amount,
                    "account_id": line_account,
                })
            ],
        }
        credit_note = self.env["account.move"].create(credit_vals)
        credit_note.action_post()
        return credit_note

    def action_view_credit_note(self):
        self.ensure_one()
        if not self.credit_note_id:
            raise UserError(_("No credit note posted yet."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.credit_note_id.id,
            "view_mode": "form",
            "target": "current",
        }
