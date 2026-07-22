# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivFeeQuota(models.Model):
    _name = "univ.fee.quota"
    _description = "Admission Quota"
    _order = "sequence, name"

    name = fields.Char(string="Quota", required=True, translate=True,
                       help="e.g. Management, Government, NRI, Sports")
    code = fields.Char(string="Code")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The quota code must be unique."),
    ]
