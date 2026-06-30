# -*- coding: utf-8 -*-
from odoo import fields, models


class InomApprovalTeamApprover(models.Model):
    _name = 'inom.approval.team.approver'
    _description = 'Contract Approval Team Approver'
    _order = 'team_id, sequence, id'

    team_id = fields.Many2one(
        comodel_name='inom.approval.team',
        string='Team',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Approver',
        required=True,
        help='User who can approve the contract.',
    )
    role = fields.Char(
        string='Role/Position',
        help='Role or position of this approver (informational).',
    )
    can_edit = fields.Boolean(
        string='Can Edit',
        help='Allow this approver to edit the contract.',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    min_amount = fields.Monetary(
        string='Minimum Amount',
        currency_field='currency_id',
        help='Minimum contract amount this approver handles.',
    )
    max_amount = fields.Monetary(
        string='Maximum Amount',
        currency_field='currency_id',
        help='Maximum contract amount this approver handles.',
    )
    condition_code = fields.Char(
        string='Custom Condition Code',
        help='Optional custom condition code for advanced rules.',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='team_id.company_id',
        string='Company',
        store=True,
    )
