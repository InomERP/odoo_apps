# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class UnivLmsGradeWizard(models.TransientModel):
    _name = "univ.lms.grade.wizard"
    _description = "Grade Submission"

    submission_id = fields.Many2one(comodel_name="univ.assignment.submission",
                                    string="Submission", required=True)
    grade = fields.Float(string="Grade", required=True)
    feedback = fields.Text(string="Feedback")

    def action_apply(self):
        self.ensure_one()
        if self.grade < 0 or self.grade > self.submission_id.max_marks:
            raise UserError(self.env._("Grade out of range."))
        self.submission_id.write({
            "grade": self.grade,
            "feedback": self.feedback,
            "state": "graded",
        })
        return {"type": "ir.actions.act_window_close"}
