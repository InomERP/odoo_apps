# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_univ_student = fields.Boolean(string="University Student", default=False)
    is_univ_faculty = fields.Boolean(string="University Faculty", default=False)
    is_univ_guardian = fields.Boolean(string="University Guardian", default=False)

    univ_student_ids = fields.One2many(
        comodel_name="univ.student",
        inverse_name="partner_id",
        string="Student Records",
    )
    univ_faculty_ids = fields.One2many(
        comodel_name="univ.faculty",
        inverse_name="partner_id",
        string="Faculty Records",
    )
