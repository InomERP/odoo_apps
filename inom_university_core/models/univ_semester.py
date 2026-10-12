# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivSemester(models.Model):
    _name = "univ.semester"
    _description = "Semester"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "program_id, sequence, name"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)
    sequence = fields.Integer(string="Sequence", default=1)
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="program_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    section_ids = fields.One2many(
        comodel_name="univ.section", inverse_name="semester_id", string="Sections"
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The semester code must be unique per campus.",
        ),
    ]
