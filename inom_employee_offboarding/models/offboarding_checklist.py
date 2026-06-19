# -*- coding: utf-8 -*-
from odoo import fields, models


class InomOffboardingChecklistTemplate(models.Model):
    _name = 'inom.offboarding.checklist.template'
    _description = 'Offboarding Checklist Template'
    _order = 'sequence, id'

    name = fields.Char(
        string='Task',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    responsible = fields.Selection(
        selection=[
            ('employee', 'Employee'),
            ('manager', 'Reporting Manager'),
            ('hr', 'HR Department'),
            ('it', 'IT Department'),
            ('finance', 'Finance Department'),
        ],
        string='Responsible',
        default='hr',
        required=True,
    )
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )


class InomOffboardingChecklistLine(models.Model):
    _name = 'inom.offboarding.checklist.line'
    _description = 'Offboarding Checklist Line'
    _order = 'sequence, id'

    request_id = fields.Many2one(
        comodel_name='inom.offboarding.request',
        string='Offboarding Request',
        required=True,
        ondelete='cascade',
    )
    template_id = fields.Many2one(
        comodel_name='inom.offboarding.checklist.template',
        string='Source Template',
    )
    name = fields.Char(string='Task', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    responsible = fields.Selection(
        selection=[
            ('employee', 'Employee'),
            ('manager', 'Reporting Manager'),
            ('hr', 'HR Department'),
            ('it', 'IT Department'),
            ('finance', 'Finance Department'),
        ],
        string='Responsible',
        default='hr',
    )
    description = fields.Text(string='Description')
    is_done = fields.Boolean(string='Completed')
    remarks = fields.Char(string='Remarks')