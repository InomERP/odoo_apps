# -*- coding: utf-8 -*-
from odoo import fields, models


class LawCaseType(models.Model):
    _name = "law.case.type"
    _description = "Legal Case Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    practice_area_id = fields.Many2one("law.practice.area", string="Practice Area")
    company_id = fields.Many2one(
        "res.company", string="Company",
        default=lambda self: self.env.company,
    )
    description = fields.Text()
