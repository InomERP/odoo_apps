# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivFeeInstallmentWizard(models.TransientModel):
    _name = "univ.fee.installment.wizard"
    _description = "Create Installment Plan"

    invoice_id = fields.Many2one(
        comodel_name="univ.fee.invoice",
        string="Fee Invoice",
        required=True,
    )
    frequency = fields.Selection(
        selection=[("monthly", "Monthly"), ("quarterly", "Quarterly")],
        string="Frequency",
        default="monthly",
        required=True,
    )
    count = fields.Integer(string="Installments", default=3, required=True)
    start_date = fields.Date(
        string="First Due Date", default=fields.Date.context_today, required=True
    )
    amount_total = fields.Monetary(
        string="Plan Amount", currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id", string="Currency"
    )

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.amount_total = self.invoice_id.amount_residual or \
                self.invoice_id.amount_total

    def action_create_plan(self):
        self.ensure_one()
        plan = self.env["univ.fee.installment.plan"].create(
            {
                "invoice_id": self.invoice_id.id,
                "frequency": self.frequency,
                "count": self.count,
                "start_date": self.start_date,
                "amount_total": self.amount_total,
            }
        )
        plan.generate_schedule()
        self.invoice_id.installment_plan_id = plan.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.fee.installment.plan",
            "res_id": plan.id,
            "view_mode": "form",
            "target": "current",
        }
