# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivExamSeat(models.Model):
    _name = "univ.exam.seat"
    _description = "Exam Seat Allocation"
    _order = "schedule_id, room_id, seat_no"

    schedule_id = fields.Many2one(
        comodel_name="univ.exam.schedule", string="Exam Schedule", required=True,
        ondelete="cascade", index=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student", required=True,
        ondelete="restrict", index=True,
    )
    room_id = fields.Many2one(comodel_name="univ.room", string="Hall", required=True)
    seat_no = fields.Char(string="Seat No.")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="schedule_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("schedule_student_uniq", "unique(schedule_id, student_id)",
         "A student gets one seat per exam schedule."),
    ]
