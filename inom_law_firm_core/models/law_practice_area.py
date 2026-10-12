# -*- coding: utf-8 -*-
from odoo import fields, models


class LawPracticeArea(models.Model):
    _name = "law.practice.area"
    _description = "Legal Practice Area"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string="Color Index")
    company_id = fields.Many2one(
        "res.company", string="Company",
        default=lambda self: self.env.company,
    )
    description = fields.Text()

    _sql_constraints = [
        ("name_company_uniq", "unique(name, company_id)",
         "The practice area name must be unique per company."),
    ]
