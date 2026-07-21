# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivPlo(models.Model):
    _name = "univ.plo"
    _description = "Program Learning Outcome"
    _order = "program_id, code"

    name = fields.Char(string="Outcome", required=True)
    code = fields.Char(string="Code", required=True)
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program", required=True,
        ondelete="cascade", index=True,
    )
    description = fields.Text(string="Description")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="program_id.company_id", store=True,
    )
