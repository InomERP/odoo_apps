# -*- coding: utf-8 -*-
from odoo import fields, models


class LawBranch(models.Model):
    _name = "law.branch"
    _description = "Law Firm Branch"
    _order = "sequence, name"

    name = fields.Char(string="Branch Name", required=True, translate=True)
    code = fields.Char(string="Branch Code", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    manager_id = fields.Many2one("res.users", string="Branch Manager")
    partner_id = fields.Many2one("res.partner", string="Address / Contact")
    phone = fields.Char()
    email = fields.Char()

    _sql_constraints = [
        ("code_company_uniq", "unique(code, company_id)",
         "The branch code must be unique per company."),
    ]
