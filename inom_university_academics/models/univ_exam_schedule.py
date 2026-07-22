# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivExamSchedule(models.Model):
    _name = "univ.exam.schedule"
    _description = "Exam Schedule Line"
    _inherit = ["mail.thread"]
    _order = "date, start_time"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    exam_id = fields.Many2one(
        comodel_name="univ.exam", string="Exam", required=True,
        ondelete="cascade", index=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject", required=True,
        ondelete="restrict", index=True,
    )
    date = fields.Date(string="Date", required=True)
    start_time = fields.Float(string="Start Time")
    end_time = fields.Float(string="End Time")
    room_id = fields.Many2one(comodel_name="univ.room", string="Hall / Room")
    max_marks = fields.Float(string="Max Marks", default=100.0, required=True)
    pass_marks = fields.Float(string="Pass Marks", default=40.0)
    is_practical = fields.Boolean(string="Practical / Viva")
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program",
        related="exam_id.program_id", store=True,
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester", string="Semester",
        related="exam_id.semester_id", store=True,
    )
    invigilator_ids = fields.One2many(
        comodel_name="univ.exam.invigilator", inverse_name="schedule_id",
        string="Invigilators",
    )
    seat_ids = fields.One2many(
        comodel_name="univ.exam.seat", inverse_name="schedule_id",
        string="Seating",
    )
    result_line_ids = fields.One2many(
        comodel_name="univ.exam.result.line", inverse_name="schedule_id",
        string="Marks",
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="exam_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("exam_subject_uniq", "unique(exam_id, subject_id)",
         "A subject is scheduled only once per exam."),
    ]

    @api.depends("exam_id", "subject_id")
    def _compute_name(self):
        for record in self:
            record.name = " - ".join(p for p in [
                record.exam_id.name, record.subject_id.code
                or record.subject_id.display_name,
            ] if p)

    def _eligible_students(self):
        self.ensure_one()
        return self.env["univ.student"].search([
            ("program_id", "=", self.program_id.id),
            ("semester_id", "=", self.semester_id.id),
            ("state", "=", "active"),
        ])

    def action_generate_result_lines(self):
        """Create empty mark lines for eligible students."""
        for record in self:
            existing = record.result_line_ids.mapped("student_id")
            vals = [
                (0, 0, {
                    "student_id": student.id,
                    "max_marks": record.max_marks,
                })
                for student in record._eligible_students()
                if student not in existing
            ]
            if vals:
                record.result_line_ids = vals
        return True

    def action_print_hall_ticket(self):
        """Hall ticket is gated on fee clearance (Phase 3 defaulter flag)."""
        self.ensure_one()
        students = self._eligible_students()
        blocked = students.filtered("is_fee_defaulter")
        if blocked:
            raise UserError(_(
                "Hall tickets blocked for fee defaulters: %s",
                ", ".join(blocked.mapped("display_name")),
            ))
        return self.env.ref(
            "inom_university_academics.action_report_hall_ticket"
        ).report_action(self)
