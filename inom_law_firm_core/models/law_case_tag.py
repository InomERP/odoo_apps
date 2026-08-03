# -*- coding: utf-8 -*-
from odoo import fields, models


class LawCaseTag(models.Model):
    _name = "law.case.tag"
    _description = "Legal Case Tag"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string="Color Index")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "The tag name must be unique."),
    ]
