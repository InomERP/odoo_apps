# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivScholarshipAward(models.Model):
    _name = "univ.scholarship.award"
    _description = "Scholarship Award"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Reference", copy=False, readonly=True,
        default=lambda self: _("New"),
    )
    scheme_id = fields.Many2one(
        comodel_name="univ.scholarship.scheme",
        string="Scheme",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student",
        string="Student",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    invoice_id = fields.Many2one(
        comodel_name="univ.fee.invoice",
        string="Applied to Invoice",
        ondelete="set null",
        help="Fee invoice the award is adjusted against (optional).",
    )
    amount = fields.Monetary(
        string="Award Amount", required=True, currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("disbursed", "Disbursed"),
            ("refused", "Refused"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    credit_note_id = fields.Many2one(
        comodel_name="account.move", string="Adjustment Entry", copy=False,
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (_("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.scholarship.award"
                ) or "SCH/0001"
        return super().create(vals_list)

    @api.onchange("scheme_id", "invoice_id")
    def _onchange_scheme_id(self):
        if self.scheme_id:
            invoice = self.invoice_id
            if invoice:
                self.amount = self.scheme_id.compute_award_amount(invoice)
            elif self.scheme_id.amount_type == "fixed":
                self.amount = self.scheme_id.amount

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted awards can be approved."))
            record.state = "approved"

    def action_refuse(self):
        self.write({"state": "refused"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_disburse(self):
        """Post a concession credit note against the linked fee invoice.

        Keeps everything inside Odoo Accounting (no parallel ledger). When no
        invoice is linked, the award is simply marked as disbursed for record.
        """
        for record in self:
            if record.state != "approved":
                raise UserError(
                    _("Approve the award before disbursing it.")
                )
            if record.invoice_id and record.invoice_id.move_id:
                record.credit_note_id = record._create_adjustment().id
            record.state = "disbursed"
            record.message_post(
                body=_("Scholarship of %s disbursed.", record.amount)
            )

    def _create_adjustment(self):
        self.ensure_one()
        move = self.invoice_id.move_id
        line_account = False
        for line in move.invoice_line_ids:
            line_account = line.account_id.id
            break
        credit_vals = {
            "move_type": "out_refund",
            "partner_id": move.partner_id.id,
            "invoice_origin": move.name,
            "ref": _("Scholarship: %s", self.scheme_id.name),
            "journal_id": move.journal_id.id,
            "invoice_line_ids": [
                (0, 0, {
                    "name": _("Scholarship adjustment: %s", self.scheme_id.name),
                    "quantity": 1.0,
                    "price_unit": self.amount,
                    "account_id": self.scheme_id.fund_account_id.id or line_account,
                })
            ],
        }
        adjustment = self.env["account.move"].create(credit_vals)
        adjustment.action_post()
        return adjustment

    def action_view_adjustment(self):
        self.ensure_one()
        if not self.credit_note_id:
            raise UserError(_("No adjustment entry posted yet."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.credit_note_id.id,
            "view_mode": "form",
            "target": "current",
        }
