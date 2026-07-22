# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivFeeRefundWizard(models.TransientModel):
    _name = "univ.fee.refund.wizard"
    _description = "Create Refund Request"

    invoice_id = fields.Many2one(
        comodel_name="univ.fee.invoice",
        string="Fee Invoice",
        required=True,
    )
    amount = fields.Monetary(
        string="Refund Amount", required=True, currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id", string="Currency"
    )
    reason = fields.Text(string="Reason", required=True)

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        if self.invoice_id and not self.amount:
            self.amount = self.invoice_id.amount_paid

    def action_create_request(self):
        self.ensure_one()
        request = self.env["univ.fee.refund.request"].create(
            {
                "invoice_id": self.invoice_id.id,
                "amount": self.amount,
                "reason": self.reason,
            }
        )
        request.action_submit()
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.fee.refund.request",
            "res_id": request.id,
            "view_mode": "form",
            "target": "current",
        }
