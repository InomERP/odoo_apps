# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivClo(models.Model):
    _name = "univ.clo"
    _description = "Course Learning Outcome"
    _order = "subject_id, code"

    name = fields.Char(string="Outcome", required=True)
    code = fields.Char(string="Code", required=True)
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject", required=True,
        ondelete="cascade", index=True,
    )
    plo_ids = fields.Many2many(
        comodel_name="univ.plo", string="Mapped Program Outcomes",
    )
    description = fields.Text(string="Description")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="subject_id.company_id", store=True,
    )
