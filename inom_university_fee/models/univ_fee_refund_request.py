# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivFeeRefundRequest(models.Model):
    _name = "univ.fee.refund.request"
    _description = "Fee Refund Request"
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
    amount = fields.Monetary(
        string="Refund Amount", required=True, currency_field="currency_id",
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
            ("l1_approved", "First Approval"),
            ("approved", "Approved"),
            ("refused", "Refused"),
            ("done", "Credit Note Posted"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    needs_second_level = fields.Boolean(
        string="Two-level Approval", compute="_compute_needs_second_level",
        store=True,
    )
    credit_note_id = fields.Many2one(
        comodel_name="account.move", string="Credit Note", copy=False,
        readonly=True,
    )
    approver_l1_id = fields.Many2one(
        comodel_name="res.users", string="Approved By", readonly=True
    )
    approver_l2_id = fields.Many2one(
        comodel_name="res.users", string="Final Approver", readonly=True
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
                    "univ.fee.refund.request"
                ) or "REF/0001"
        return super().create(vals_list)

    @api.depends("amount", "company_id.fee_refund_threshold")
    def _compute_needs_second_level(self):
        for record in self:
            threshold = record.company_id.fee_refund_threshold or 0.0
            record.needs_second_level = bool(threshold) and record.amount > threshold

    @api.constrains("amount")
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise UserError(_("Refund amount must be positive."))
            if record.invoice_id and record.amount > record.invoice_id.amount_total:
                raise UserError(
                    _("Refund cannot exceed the invoice total.")
                )

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        """First-level approval (accounts officer)."""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be approved."))
            record.approver_l1_id = self.env.user.id
            if record.needs_second_level:
                record.state = "l1_approved"
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary=_("Refund needs registrar approval"),
                )
            else:
                record.state = "approved"

    def action_approve_final(self):
        """Second-level approval (registrar) for large refunds."""
        for record in self:
            if record.state != "l1_approved":
                raise UserError(
                    _("This request is not awaiting final approval.")
                )
            record.approver_l2_id = self.env.user.id
            record.state = "approved"

    def action_refuse(self):
        self.write({"state": "refused"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_post_credit_note(self):
        for record in self:
            if record.state != "approved":
                raise UserError(
                    _("Approve the refund before posting a credit note.")
                )
            if not record.move_id:
                raise UserError(
                    _("The fee invoice has no posted journal entry.")
                )
            credit_note = record._create_credit_note()
            record.credit_note_id = credit_note.id
            record.state = "done"
            record.message_post(
                body=_(
                    "Credit note %s posted for refund of %s.",
                    credit_note.name,
                    record.amount,
                )
            )

    def _create_credit_note(self):
        self.ensure_one()
        move = self.move_id
        # Build a single-line credit note for the refunded amount, reusing the
        # receivable/income setup of the source invoice. No parallel ledger.
        line_account = False
        for line in move.invoice_line_ids:
            line_account = line.account_id.id
            break
        credit_vals = {
            "move_type": "out_refund",
            "partner_id": move.partner_id.id,
            "invoice_origin": move.name,
            "ref": _("Refund of %s", move.name),
            "journal_id": move.journal_id.id,
            "invoice_line_ids": [
                (0, 0, {
                    "name": _("Fee refund: %s", self.reason or ""),
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
