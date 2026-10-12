# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivExamType(models.Model):
    _name = "univ.exam.type"
    _description = "Examination Type"
    _order = "sequence, name"

    name = fields.Char(string="Exam Type", required=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(string="Sequence", default=10)
    category = fields.Selection(
        selection=[
            ("internal", "Internal Assessment"),
            ("mid", "Mid Term"),
            ("final", "Final / Semester"),
            ("practical", "Practical"),
            ("viva", "Viva"),
        ],
        string="Category", default="internal", required=True,
    )
    weightage = fields.Float(
        string="Weightage %", default=100.0,
        help="Contribution of this exam type to the subject's final marks.",
    )
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True,
    )

    _sql_constraints = [
        ("code_uniq", "unique(code, company_id)",
         "The exam type code must be unique per company."),
    ]
