# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivLessonPlan(models.Model):
    _name = "univ.lesson.plan"
    _description = "Lesson Plan"
    _order = "planned_date, id"

    name = fields.Char(string="Topic", required=True)
    unit_id = fields.Many2one(
        comodel_name="univ.syllabus.unit", string="Syllabus Unit",
        required=True, ondelete="cascade", index=True,
    )
    syllabus_id = fields.Many2one(
        comodel_name="univ.syllabus", string="Syllabus",
        related="unit_id.syllabus_id", store=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject",
        related="syllabus_id.subject_id", store=True,
    )
    faculty_id = fields.Many2one(comodel_name="univ.faculty", string="Faculty")
    planned_date = fields.Date(string="Planned Date")
    duration_hours = fields.Float(string="Duration (h)", default=1.0)
    state = fields.Selection(
        selection=[("planned", "Planned"), ("delivered", "Delivered"),
                   ("postponed", "Postponed")],
        string="Status", default="planned",
    )
    methodology = fields.Text(string="Methodology / Resources")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="syllabus_id.company_id", store=True,
    )

    def action_mark_delivered(self):
        self.write({"state": "delivered"})
