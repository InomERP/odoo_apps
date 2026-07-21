# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivExamInvigilator(models.Model):
    _name = "univ.exam.invigilator"
    _description = "Invigilation Duty"
    _order = "schedule_id, id"

    schedule_id = fields.Many2one(
        comodel_name="univ.exam.schedule", string="Exam Schedule", required=True,
        ondelete="cascade", index=True,
    )
    faculty_id = fields.Many2one(
        comodel_name="univ.faculty", string="Invigilator", required=True,
        ondelete="restrict", index=True,
    )
    date = fields.Date(string="Date", related="schedule_id.date", store=True)
    room_id = fields.Many2one(
        comodel_name="univ.room", string="Hall",
        related="schedule_id.room_id", store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="schedule_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("schedule_faculty_uniq", "unique(schedule_id, faculty_id)",
         "Faculty assigned only once per exam schedule."),
    ]

    @api.constrains("faculty_id", "date")
    def _check_conflict(self):
        """A faculty cannot invigilate two exams on the same date/time slot."""
        for record in self:
            clashes = self.search([
                ("id", "!=", record.id),
                ("faculty_id", "=", record.faculty_id.id),
                ("date", "=", record.date),
            ])
            for other in clashes:
                a_s, a_e = record.schedule_id.start_time, record.schedule_id.end_time
                b_s, b_e = other.schedule_id.start_time, other.schedule_id.end_time
                if a_s < b_e and b_s < a_e:
                    raise ValidationError(_(
                        "Invigilation conflict for %(f)s on %(d)s.",
                        f=record.faculty_id.display_name, d=record.date,
                    ))
