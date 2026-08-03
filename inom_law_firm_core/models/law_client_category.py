# -*- coding: utf-8 -*-
from odoo import fields, models


class LawClientCategory(models.Model):
    _name = "law.client.category"
    _description = "Legal Client Category"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string="Color Index")
    active = fields.Boolean(default=True)
    description = fields.Text()
