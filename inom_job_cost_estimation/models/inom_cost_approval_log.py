# -*- coding: utf-8 -*-
from odoo import fields, models


class InomCostApprovalLog(models.Model):
    """Immutable record of every state change on an estimate.

    The chatter already narrates this, but chatter is filtered, translated and
    hard to report on. A dedicated model gives an auditor a list they can sort,
    group and export - which is usually the reason job costing gets bought in
    the first place.
    """
    _name = 'inom.cost.approval.log'
    _description = 'Job Cost Estimate Approval History'
    _order = 'date desc, id desc'

    estimate_id = fields.Many2one('inom.cost.estimate', string='Estimate',
                                  required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Changed By',
                              default=lambda self: self.env.user)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    state_from = fields.Char(string='From')
    state_to = fields.Char(string='To')
    amount_total = fields.Monetary(string='Total at the time',
                                   currency_field='currency_id')
    currency_id = fields.Many2one(related='estimate_id.currency_id')
    note = fields.Char(string='Note')
