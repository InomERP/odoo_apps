# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivSubject(models.Model):
    _inherit = "univ.subject"

    clo_ids = fields.One2many(
        comodel_name="univ.clo", inverse_name="subject_id",
        string="Course Learning Outcomes",
    )
    syllabus_ids = fields.One2many(
        comodel_name="univ.syllabus", inverse_name="subject_id",
        string="Syllabi",
    )
