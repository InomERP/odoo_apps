# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivAttendanceSummary(models.Model):
    _name = "univ.attendance.summary"
    _description = "Attendance Summary (per student / subject)"
    _order = "student_id, subject_id"

    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student", required=True,
        ondelete="cascade", index=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject", required=True,
        ondelete="cascade", index=True,
    )
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program",
        related="student_id.program_id", store=True,
    )
    held = fields.Integer(string="Periods Held")
    attended = fields.Integer(string="Attended")
    percent = fields.Float(string="Attendance %")
    shortage_band = fields.Selection(
        selection=[
            ("ok", "OK (>= 85%)"),
            ("w85", "Below 85%"),
            ("w75", "Below 75%"),
            ("w65", "Below 65% (Critical)"),
        ],
        string="Shortage Band", default="ok",
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="student_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("student_subject_uniq", "unique(student_id, subject_id)",
         "One summary row per student and subject."),
    ]

    @staticmethod
    def _band_for(percent):
        if percent < 65:
            return "w65"
        if percent < 75:
            return "w75"
        if percent < 85:
            return "w85"
        return "ok"

    @api.model
    def _cron_compute_shortage(self):
        """Weekly recompute of attendance % per student/subject + alerts."""
        Line = self.env["univ.attendance.line"]
        groups = Line._read_group(
            [("sheet_id.state", "in", ("submitted", "locked"))],
            groupby=["student_id", "subject_id"],
            aggregates=["__count"],
        )
        existing = {
            (s.student_id.id, s.subject_id.id): s for s in self.search([])
        }
        seen = set()
        for student, subject, _count in groups:
            if not student or not subject:
                continue
            lines = Line.search([
                ("student_id", "=", student.id),
                ("subject_id", "=", subject.id),
                ("sheet_id.state", "in", ("submitted", "locked")),
            ])
            held = len(lines)
            attended = len(lines.filtered(
                lambda l: l.state in ("present", "late")
            ))
            percent = (attended / held * 100.0) if held else 0.0
            band = self._band_for(percent)
            vals = {
                "held": held, "attended": attended,
                "percent": percent, "shortage_band": band,
            }
            key = (student.id, subject.id)
            seen.add(key)
            record = existing.get(key)
            if record:
                record.write(vals)
            else:
                record = self.create(dict(
                    vals, student_id=student.id, subject_id=subject.id
                ))
            if band in ("w75", "w65"):
                record._notify_shortage()

    def _notify_shortage(self):
        self.ensure_one()
        student = self.student_id
        student.activity_schedule(
            "mail.mail_activity_data_todo",
            summary=self.env._(
                "Attendance shortage in %(subj)s: %(pct).1f%%",
                subj=self.subject_id.display_name, pct=self.percent,
            ),
        ) if student else None
