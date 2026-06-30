# -*- coding: utf-8 -*-
from odoo import fields, models


class InomApprovalTeam(models.Model):
    _name = 'inom.approval.team'
    _description = 'Contract Approval Team'
    _order = 'sequence, name'

    name = fields.Char(string='Team Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    contract_type = fields.Selection(
        selection=[
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('all', 'All'),
        ],
        string='Applies To',
        default='all',
        required=True,
        help='Type of contracts this team can be used for.',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    team_leader_id = fields.Many2one(
        comodel_name='res.users',
        string='Team Leader',
    )
    member_ids = fields.Many2many(
        comodel_name='res.users',
        string='Members',
    )
    step_ids = fields.One2many(
        comodel_name='inom.approval.step',
        inverse_name='team_id',
        string='Approval Steps',
        copy=True,
    )
    approver_line_ids = fields.One2many(
        comodel_name='inom.approval.team.approver',
        inverse_name='team_id',
        string='Approvers',
        copy=True,
    )
    note = fields.Text(string='Notes')