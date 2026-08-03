# -*- coding: utf-8 -*-
from odoo import fields, models


class LawSpecialization(models.Model):
    _name = "law.specialization"
    _description = "Legal Specialization"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    description = fields.Text()
