# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    univ_student_prefix = fields.Char(
        string="Student Enrolment Prefix",
        default="STU",
        help="Campus-aware prefix prepended to the auto-generated student "
        "enrolment number, e.g. 'STU' produces STU/2026/0001.",
    )
    univ_faculty_prefix = fields.Char(
        string="Faculty Code Prefix",
        default="FAC",
        help="Campus-aware prefix prepended to the auto-generated faculty code.",
    )
