# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UnivApplicantMerit(models.Model):
    _name = "univ.applicant.merit"
    _description = "Applicant Merit / Entrance Score"
    _order = "applicant_id, sequence, id"

    applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Applicant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    source = fields.Selection(
        selection=[
            ("entrance_exam", "Entrance Exam"),
            ("board_marks", "Board Marks"),
            ("interview", "Interview"),
            ("portfolio", "Portfolio"),
            ("other", "Other"),
        ],
        string="Source",
        required=True,
        default="entrance_exam",
    )
    reference = fields.Char(string="Reference / Exam")
    score = fields.Float(string="Score", required=True)
    max_score = fields.Float(string="Out Of", default=100.0)
    weight = fields.Float(
        string="Weight %",
        default=100.0,
        help="Relative weight of this component in the overall merit score.",
    )
    weighted_score = fields.Float(
        string="Weighted Score", compute="_compute_weighted_score", store=True
    )
    score_date = fields.Date(string="Date")
    remark = fields.Char(string="Remark")

    @api.depends("score", "max_score", "weight")
    def _compute_weighted_score(self):
        for record in self:
            normalised = (
                (record.score / record.max_score) if record.max_score else 0.0
            )
            record.weighted_score = normalised * record.weight

    @api.constrains("score", "max_score")
    def _check_score(self):
        for record in self:
            if record.max_score and record.score > record.max_score:
                raise ValidationError(
                    self.env._("Score cannot exceed the maximum score.")
                )
            if record.score < 0:
                raise ValidationError(self.env._("Score cannot be negative."))
