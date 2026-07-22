# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivFeeGroup(models.Model):
    _name = "univ.fee.group"
    _description = "Fee Group"
    _order = "sequence, name"

    name = fields.Char(string="Fee Group", required=True, translate=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(string="Sequence", default=10)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The fee group code must be unique."),
    ]
