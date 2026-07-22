# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivAcademicCalendar(models.Model):
    _name = "univ.academic.calendar"
    _description = "Academic Calendar Event"
    _order = "date, id"

    name = fields.Char(string="Event", required=True)
    date = fields.Date(string="Date", required=True)
    date_to = fields.Date(string="End Date")
    event_type = fields.Selection(
        selection=[
            ("term", "Term Start/End"),
            ("holiday", "Holiday"),
            ("exam", "Examination"),
            ("event", "Event"),
            ("deadline", "Deadline"),
        ],
        string="Type",
        default="event",
        required=True,
    )
    academic_year_id = fields.Many2one(
        comodel_name="univ.academic.session", string="Academic Year"
    )
    program_id = fields.Many2one(comodel_name="univ.program", string="Program")
    description = fields.Text(string="Description")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True,
    )
