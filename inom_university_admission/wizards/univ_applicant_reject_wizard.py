# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class UnivApplicantRejectWizard(models.TransientModel):
    _name = "univ.applicant.reject.wizard"
    _description = "Reject Applicant Wizard"

    applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Applicant",
        required=True,
    )
    reason = fields.Text(string="Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.applicant_id:
            raise UserError(self.env._("No applicant selected."))
        self.applicant_id._do_reject(self.reason)
        return {"type": "ir.actions.act_window_close"}
