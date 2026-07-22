# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivSection(models.Model):
    _inherit = "univ.section"

    session_ids = fields.One2many(
        comodel_name="univ.timetable.session", inverse_name="section_id",
        string="Timetable Sessions",
    )
    confirmed_session_ids = fields.One2many(
        comodel_name="univ.timetable.session", inverse_name="section_id",
        string="Confirmed Sessions",
        domain=[("state", "=", "confirmed")],
    )
