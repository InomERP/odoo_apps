# -*- coding: utf-8 -*-
# Phase 2 - Conditional Acceptance.
# A condition is an outstanding requirement attached to a conditional offer
# (e.g. "Pending final transcript"). Enrolment is gated until every condition
# is cleared (satisfied or waived). Purely additive: no existing model touched.
from odoo import api, fields, models


class UnivApplicantCondition(models.Model):
    _name = "univ.applicant.condition"
    _description = "Conditional Admission Requirement"
    _inherit = ["mail.thread"]
    _order = "sequence, id"

    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Condition", required=True, tracking=True)
    instructions = fields.Text(
        string="Submission Instructions",
        help="What the applicant must do to satisfy this condition.",
    )
    applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Applicant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    offer_id = fields.Many2one(
        comodel_name="univ.applicant.offer",
        string="Conditional Offer",
        ondelete="set null",
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("satisfied", "Satisfied"),
            ("waived", "Waived"),
        ],
        string="Status",
        default="pending",
        required=True,
        tracking=True,
    )
    satisfied_on = fields.Datetime(string="Cleared On", readonly=True, copy=False)
    satisfied_by = fields.Many2one(
        comodel_name="res.users",
        string="Cleared By",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="applicant_id.company_id",
        store=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------
    def _set_cleared(self, state):
        self.write(
            {
                "state": state,
                "satisfied_on": fields.Datetime.now(),
                "satisfied_by": self.env.user.id,
            }
        )
        # Notify the applicant aggregate so it can attempt auto-enrolment and
        # let the applicant know once nothing is outstanding.
        for applicant in self.mapped("applicant_id"):
            applicant._on_conditions_resolved()

    def action_mark_satisfied(self):
        self._set_cleared("satisfied")

    def action_waive(self):
        self._set_cleared("waived")

    def action_mark_pending(self):
        self.write(
            {"state": "pending", "satisfied_on": False, "satisfied_by": False}
        )
