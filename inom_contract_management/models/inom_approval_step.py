# -*- coding: utf-8 -*-
from odoo import fields, models


class InomApprovalStep(models.Model):
    _name = 'inom.approval.step'
    _description = 'Contract Approval Step'
    _order = 'team_id, sequence, id'

    team_id = fields.Many2one(
        comodel_name='inom.approval.team',
        string='Team',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(
        string='Level',
        default=1,
        help='Order of this approval step (Level 1, 2, 3 ...).',
    )
    name = fields.Char(
        string='Step Name',
        required=True,
    )
    approver_ids = fields.Many2many(
        comodel_name='res.users',
        string='Approvers',
        required=True,
        help='Users who must approve the contract at this step.',
    )
    company_id = fields.Many2one(
        related='team_id.company_id',
        string='Company',
        store=True,
    )