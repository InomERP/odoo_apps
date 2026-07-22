# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivFeeCategory(models.Model):
    _name = "univ.fee.category"
    _description = "Fee Category"
    _order = "sequence, name"

    name = fields.Char(string="Category", required=True, translate=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(string="Sequence", default=10)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The fee category code must be unique."),
    ]
