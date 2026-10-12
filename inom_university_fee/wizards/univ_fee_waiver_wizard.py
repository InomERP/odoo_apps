# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivFeeWaiverWizard(models.TransientModel):
    _name = "univ.fee.waiver.wizard"
    _description = "Create Fee Waiver"

    invoice_id = fields.Many2one(
        comodel_name="univ.fee.invoice",
        string="Fee Invoice",
        required=True,
    )
    waiver_type = fields.Selection(
        selection=[("full", "Full Waiver"), ("partial", "Partial Waiver")],
        string="Waiver Type",
        default="partial",
        required=True,
    )
    amount = fields.Monetary(
        string="Waiver Amount", required=True, currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id", string="Currency"
    )
    reason = fields.Text(string="Reason", required=True)

    @api.onchange("invoice_id", "waiver_type")
    def _onchange_invoice_id(self):
        if self.invoice_id:
            if self.waiver_type == "full":
                self.amount = self.invoice_id.amount_residual or \
                    self.invoice_id.amount_total
            elif not self.amount:
                self.amount = 0.0

    def action_create_waiver(self):
        self.ensure_one()
        waiver = self.env["univ.fee.waiver"].create(
            {
                "invoice_id": self.invoice_id.id,
                "waiver_type": self.waiver_type,
                "amount": self.amount,
                "reason": self.reason,
            }
        )
        waiver.action_submit()
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.fee.waiver",
            "res_id": waiver.id,
            "view_mode": "form",
            "target": "current",
        }
