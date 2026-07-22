# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivStudent(models.Model):
    _inherit = "univ.student"

    attendance_summary_ids = fields.One2many(
        comodel_name="univ.attendance.summary", inverse_name="student_id",
        string="Attendance Summary",
    )
    semester_result_ids = fields.One2many(
        comodel_name="univ.result.semester", inverse_name="student_id",
        string="Semester Results",
    )
    overall_attendance = fields.Float(
        string="Overall Attendance %", compute="_compute_academic", store=False,
    )
    current_cgpa = fields.Float(
        string="CGPA", compute="_compute_academic", store=False,
    )
    has_attendance_shortage = fields.Boolean(
        string="Attendance Shortage", compute="_compute_academic", store=False,
    )

    def _compute_academic(self):
        for student in self:
            summaries = student.attendance_summary_ids
            held = sum(summaries.mapped("held"))
            attended = sum(summaries.mapped("attended"))
            student.overall_attendance = (attended / held * 100.0) if held else 0.0
            student.has_attendance_shortage = any(
                s.shortage_band in ("w75", "w65") for s in summaries
            )
            published = student.semester_result_ids.filtered("published")
            credits = sum(published.mapped("total_credits"))
            weighted = sum(r.sgpa * r.total_credits for r in published)
            student.current_cgpa = (weighted / credits) if credits else 0.0

    # ---- Smart-button actions ----
    def action_view_attendance(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Attendance"),
            "res_model": "univ.attendance.summary",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
        }

    def action_view_results(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Results"),
            "res_model": "univ.result.semester",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
        }
