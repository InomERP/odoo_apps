# -*- coding: utf-8 -*-
from odoo import fields, models


class InomContractApprover(models.Model):
    _name = 'inom.contract.approver'
    _description = 'Contract Approver'
    _order = 'contract_id, step, id'

    contract_id = fields.Many2one(
        comodel_name='inom.contract',
        string='Contract',
        required=True,
        ondelete='cascade',
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Approver',
        required=True,
    )
    role = fields.Char(
        string='Role/Position',
        help='Role or position of this approver, copied from the approval team.',
    )
    step = fields.Integer(
        string='Level',
        default=1,
    )
    step_name = fields.Char(
        string='Step',
    )
    status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('returned', 'Returned'),
        ],
        string='Status',
        default='pending',
        required=True,
    )
    date = fields.Datetime(
        string='Action Date',
    )
    comment = fields.Text(
        string='Comment',
    )
    company_id = fields.Many2one(
        related='contract_id.company_id',
        string='Company',
        store=True,
    )