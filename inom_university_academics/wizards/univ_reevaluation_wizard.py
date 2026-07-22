# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivReevaluationWizard(models.TransientModel):
    _name = "univ.reevaluation.wizard"
    _description = "Apply for Re-evaluation"

    result_line_id = fields.Many2one(
        comodel_name="univ.exam.result.line", string="Result Line", required=True,
    )
    fee_paid = fields.Boolean(string="Re-evaluation Fee Paid")

    def action_create(self):
        self.ensure_one()
        reeval = self.env["univ.exam.reevaluation"].create({
            "result_line_id": self.result_line_id.id,
            "fee_paid": self.fee_paid,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.exam.reevaluation",
            "res_id": reeval.id,
            "view_mode": "form",
            "target": "current",
        }
