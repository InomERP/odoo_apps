# -*- coding: utf-8 -*-
from odoo import _, fields, models


class InomCostLossReason(models.Model):
    """Why estimates are lost.

    A configurable model rather than a selection: every contractor loses work
    for its own reasons, and the list is the whole point of the analysis.
    """
    _name = 'inom.cost.loss.reason'
    _description = 'Job Cost Estimate Loss Reason'
    _order = 'sequence, id'

    name = fields.Char(string='Reason', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        'unique(name)', 'That loss reason already exists.')


class InomCostRejectWizard(models.TransientModel):
    """Asks why before letting an estimate be marked lost.

    Rejecting without a reason is the easiest way to end up with a win/loss
    report nobody can act on, so the reason is required here.
    """
    _name = 'inom.cost.reject.wizard'
    _description = 'Reject Job Cost Estimate'

    estimate_id = fields.Many2one('inom.cost.estimate', string='Estimate',
                                  required=True, ondelete='cascade')
    loss_reason_id = fields.Many2one('inom.cost.loss.reason',
                                     string='Loss Reason', required=True)
    loss_note = fields.Text(string='Details')

    def action_confirm(self):
        self.ensure_one()
        self.estimate_id.write({
            'loss_reason_id': self.loss_reason_id.id,
            'loss_note': self.loss_note,
        })
        self.estimate_id.action_reject()
        return {'type': 'ir.actions.act_window_close'}
