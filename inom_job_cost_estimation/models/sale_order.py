# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    inom_estimate_id = fields.Many2one(
        'inom.cost.estimate', string='Job Cost Estimate', copy=False,
        readonly=True, index='btree_not_null',
        help='Job cost estimate this quotation was generated from.')
    inom_estimate_count = fields.Integer(compute='_compute_inom_estimate_count')

    @api.depends('inom_estimate_id')
    def _compute_inom_estimate_count(self):
        for order in self:
            order.inom_estimate_count = 1 if order.inom_estimate_id else 0

    def action_view_inom_estimate(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Job Cost Estimate'),
            'res_model': 'inom.cost.estimate',
            'res_id': self.inom_estimate_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
