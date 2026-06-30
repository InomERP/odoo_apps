# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

APPROVER_GROUP = 'inom_stock_adjust_control.group_stock_adjust_approver'


class StockAdjustRejectWizard(models.TransientModel):
    _name = 'stock.adjust.reject.wizard'
    _description = 'Inventory Adjustment Rejection'

    reason = fields.Text(string='Rejection Reason', required=True)
    quant_ids = fields.Many2many('stock.quant', string='Adjustments')

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        quants = self.env['stock.quant'].browse(active_ids).filtered(
            lambda q: q.adjust_approval_state == 'to_approve')
        result['quant_ids'] = [(6, 0, quants.ids)]
        return result

    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group(APPROVER_GROUP):
            raise UserError(_('Only an Inventory Adjustment Approver can reject adjustments.'))
        if not self.quant_ids:
            raise UserError(_('There is no adjustment waiting for approval to reject.'))
        for quant in self.quant_ids:
            quant.write({
                'adjust_approval_state': 'rejected',
                'adjust_approver_id': self.env.user.id,
                'adjust_reject_reason': self.reason,
            })
            quant._adjust_clear_activities()
            quant._adjust_revert_count()
            quant.message_post(
                body=_('Inventory adjustment rejected by %(user)s. Reason: %(reason)s',
                       user=self.env.user.display_name, reason=self.reason)
            )
        return {'type': 'ir.actions.act_window_close'}
