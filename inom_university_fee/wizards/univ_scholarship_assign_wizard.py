# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivScholarshipAssignWizard(models.TransientModel):
    _name = "univ.scholarship.assign.wizard"
    _description = "Assign Scholarship"

    scheme_id = fields.Many2one(
        comodel_name="univ.scholarship.scheme",
        string="Scheme",
        required=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student", required=True
    )
    invoice_id = fields.Many2one(
        comodel_name="univ.fee.invoice",
        string="Apply to Invoice",
        domain="[('student_id', '=', student_id)]",
    )
    amount = fields.Monetary(string="Amount", currency_field="currency_id")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    @api.onchange("scheme_id", "invoice_id")
    def _onchange_scheme(self):
        if self.scheme_id:
            if self.invoice_id:
                self.amount = self.scheme_id.compute_award_amount(self.invoice_id)
            elif self.scheme_id.amount_type == "fixed":
                self.amount = self.scheme_id.amount

    def action_assign(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Award amount must be positive."))
        award = self.env["univ.scholarship.award"].create(
            {
                "scheme_id": self.scheme_id.id,
                "student_id": self.student_id.id,
                "invoice_id": self.invoice_id.id or False,
                "amount": self.amount,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.scholarship.award",
            "res_id": award.id,
            "view_mode": "form",
            "target": "current",
        }
