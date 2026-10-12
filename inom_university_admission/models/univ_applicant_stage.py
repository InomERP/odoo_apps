# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivApplicantStage(models.Model):
    _name = "univ.applicant.stage"
    _description = "Admission Pipeline Stage"
    _order = "sequence, id"

    name = fields.Char(string="Stage", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", default=10)
    code = fields.Char(
        string="Technical Code",
        help="Optional stable code used by automated transitions.",
    )
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        ondelete="cascade",
        index=True,
        help="Leave empty for a stage shared by every program.",
    )
    fold = fields.Boolean(
        string="Folded in Kanban",
        help="Folded stages are collapsed in the pipeline kanban view.",
    )
    is_default = fields.Boolean(
        string="Default Stage",
        help="New applications start in the default stage.",
    )
    is_won = fields.Boolean(
        string="Enrolled Stage",
        help="Applicants reaching this stage are considered enrolled.",
    )
    is_rejected = fields.Boolean(
        string="Rejected Stage",
        help="Applicants reaching this stage are considered rejected/withdrawn.",
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    applicant_count = fields.Integer(
        string="Applicants", compute="_compute_applicant_count"
    )

    def _compute_applicant_count(self):
        data = self.env["univ.applicant"]._read_group(
            [("stage_id", "in", self.ids)],
            groupby=["stage_id"],
            aggregates=["__count"],
        )
        mapped = {stage.id: count for stage, count in data}
        for stage in self:
            stage.applicant_count = mapped.get(stage.id, 0)
