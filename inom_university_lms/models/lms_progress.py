# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class UnivLmsProgress(models.Model):
    _name = "univ.lms.progress"
    _description = "Learning Progress"
    _auto = False
    _order = "subject_id, student_id"

    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 readonly=True)
    subject_id = fields.Many2one(comodel_name="univ.subject", string="Subject",
                                 readonly=True)
    submitted_count = fields.Integer(string="Submitted", readonly=True)
    graded_count = fields.Integer(string="Graded", readonly=True)
    late_count = fields.Integer(string="Late", readonly=True)
    avg_grade = fields.Float(string="Average Grade", readonly=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(s.id) AS id,
                    s.student_id AS student_id,
                    a.subject_id AS subject_id,
                    COUNT(s.id) AS submitted_count,
                    COUNT(s.id) FILTER (WHERE s.state = 'graded') AS graded_count,
                    COUNT(s.id) FILTER (WHERE s.is_late) AS late_count,
                    AVG(s.grade) FILTER (WHERE s.state = 'graded') AS avg_grade,
                    s.company_id AS company_id
                FROM univ_assignment_submission s
                JOIN univ_assignment a ON a.id = s.assignment_id
                GROUP BY s.student_id, a.subject_id, s.company_id
            )
        """ % self._table)
