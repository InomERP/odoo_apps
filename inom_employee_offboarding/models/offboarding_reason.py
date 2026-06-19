# -*- coding: utf-8 -*-
from odoo import fields, models


class InomOffboardingReason(models.Model):
    _name = 'inom.offboarding.reason'
    _description = 'Employee Offboarding Reason'
    _order = 'sequence, name'

    name = fields.Char(
        string='Reason',
        required=True,
        translate=True,
    )
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('code_company_uniq',
         'unique(code, company_id)',
         'The reason code must be unique per company.'),
    ]