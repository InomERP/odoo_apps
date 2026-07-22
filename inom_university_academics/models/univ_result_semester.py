# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivResultSemester(models.Model):
    _name = "univ.result.semester"
    _description = "Semester Result"
    _inherit = ["mail.thread"]
    _order = "student_id, semester_id"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student", required=True,
        ondelete="cascade", index=True, tracking=True,
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester", string="Semester", required=True,
        ondelete="restrict", index=True,
    )
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program",
        related="student_id.program_id", store=True,
    )
    academic_year_id = fields.Many2one(
        comodel_name="univ.academic.session", string="Academic Year",
    )
    line_ids = fields.One2many(
        comodel_name="univ.result.semester.line", inverse_name="result_id",
        string="Subjects",
    )
    total_credits = fields.Float(string="Credits", compute="_compute_gpa",
                                 store=True)
    earned_credits = fields.Float(string="Earned Credits", compute="_compute_gpa",
                                  store=True)
    sgpa = fields.Float(string="SGPA", compute="_compute_gpa", store=True,
                        tracking=True)
    backlog_count = fields.Integer(string="Backlogs", compute="_compute_gpa",
                                   store=True)
    status = fields.Selection(
        selection=[
            ("pass", "Pass"),
            ("fail", "Fail"),
            ("backlog", "Backlog"),
            ("grace", "Grace Pass"),
        ],
        string="Result", compute="_compute_gpa", store=True,
    )
    version = fields.Integer(string="Version", default=1)
    published = fields.Boolean(string="Published", default=False, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="student_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("student_sem_uniq", "unique(student_id, semester_id)",
         "One result record per student per semester."),
    ]

    @api.depends("student_id", "semester_id")
    def _compute_name(self):
        for record in self:
            record.name = "%s - %s" % (
                record.student_id.display_name or "",
                record.semester_id.display_name or "",
            )

    @api.depends("line_ids.credit_hours", "line_ids.grade_point", "line_ids.is_pass")
    def _compute_gpa(self):
        for record in self:
            credits = sum(record.line_ids.mapped("credit_hours"))
            weighted = sum(
                l.credit_hours * l.grade_point for l in record.line_ids
            )
            earned = sum(
                l.credit_hours for l in record.line_ids if l.is_pass
            )
            backlogs = len(record.line_ids.filtered(lambda l: not l.is_pass))
            record.total_credits = credits
            record.earned_credits = earned
            record.sgpa = (weighted / credits) if credits else 0.0
            record.backlog_count = backlogs
            record.status = "pass" if backlogs == 0 and record.line_ids else (
                "backlog" if backlogs else "fail"
            )

    def action_recompute(self):
        """Rebuild subject lines from approved exam result lines."""
        for record in self:
            record.line_ids.unlink()
            lines = self.env["univ.exam.result.line"].search([
                ("student_id", "=", record.student_id.id),
                ("schedule_id.semester_id", "=", record.semester_id.id),
            ])
            vals = []
            for src in lines:
                vals.append((0, 0, {
                    "subject_id": src.subject_id.id,
                    "credit_hours": src.subject_id.credit_hours,
                    "grade": src.grade,
                    "grade_point": src.grade_point,
                    "percent": src.percent,
                    "is_pass": src.is_pass,
                }))
            record.line_ids = vals

    def action_publish(self):
        self.write({"published": True})

    def action_unpublish(self):
        self.write({"published": False})


class UnivResultSemesterLine(models.Model):
    _name = "univ.result.semester.line"
    _description = "Semester Result Line"
    _order = "result_id, subject_id"

    result_id = fields.Many2one(
        comodel_name="univ.result.semester", string="Result", required=True,
        ondelete="cascade", index=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject", required=True,
    )
    credit_hours = fields.Float(string="Credits")
    percent = fields.Float(string="%")
    grade = fields.Char(string="Grade")
    grade_point = fields.Float(string="Grade Point")
    is_pass = fields.Boolean(string="Pass")
