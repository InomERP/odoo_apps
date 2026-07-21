# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivQuota(models.Model):
    _name = "univ.quota"
    _description = "Admission Quota / Category"
    _order = "sequence, name"

    name = fields.Char(string="Quota", required=True, translate=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    seat_ids = fields.One2many(
        comodel_name="univ.quota.seat",
        inverse_name="quota_id",
        string="Seat Caps",
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            "The quota code must be unique.",
        ),
    ]
