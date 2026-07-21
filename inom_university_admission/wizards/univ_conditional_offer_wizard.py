# -*- coding: utf-8 -*-
# Phase 2 - Issue a conditional offer with one or more conditions in one step.
from odoo import _, fields, models
from odoo.exceptions import UserError


class UnivConditionalOfferWizard(models.TransientModel):
    _name = "univ.conditional.offer.wizard"
    _description = "Issue Conditional Offer"

    applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Applicant",
        required=True,
    )
    expiry_date = fields.Date(
        string="Valid Until",
        default=lambda self: fields.Date.add(fields.Date.today(), days=7),
    )
    line_ids = fields.One2many(
        comodel_name="univ.conditional.offer.wizard.line",
        inverse_name="wizard_id",
        string="Conditions",
    )

    def action_issue(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(
                _("Please define at least one condition.")
            )
        applicant = self.applicant_id
        offer = self.env["univ.applicant.offer"].create(
            {
                "applicant_id": applicant.id,
                "fee_amount": applicant.admission_fee,
                "expiry_date": self.expiry_date,
            }
        )
        self.env["univ.applicant.condition"].create(
            [
                {
                    "applicant_id": applicant.id,
                    "offer_id": offer.id,
                    "name": line.name,
                    "instructions": line.instructions,
                    "sequence": line.sequence,
                }
                for line in self.line_ids
            ]
        )
        offer.action_send_conditional()
        applicant.action_move_stage("offer")
        return {
            "type": "ir.actions.act_window",
            "name": _("Conditional Offer"),
            "res_model": "univ.applicant.offer",
            "res_id": offer.id,
            "view_mode": "form",
            "target": "current",
        }


class UnivConditionalOfferWizardLine(models.TransientModel):
    _name = "univ.conditional.offer.wizard.line"
    _description = "Conditional Offer Line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="univ.conditional.offer.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Condition", required=True)
    instructions = fields.Text(string="Submission Instructions")
