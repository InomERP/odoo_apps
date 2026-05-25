# -*- coding: utf-8 -*-
from odoo import models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _apply_inventory(self, *args, **kwargs):

        result = super()._apply_inventory(*args, **kwargs)
        self._sync_pos_stock()
        return result

    def write(self, vals):
        result = super().write(vals)
        if 'inventory_quantity' in vals or 'quantity' in vals:
            self._sync_pos_stock()
        return result

    def _sync_pos_stock(self):
        products = self.mapped('product_id.product_tmpl_id')
        products._compute_tmpl_pos_qty()
        sessions = self.env['pos.session'].search([('state', '=', 'opened')])
        for session in sessions:
            session._notify('SYNC_PRODUCT_DATA', {
                'product.template': {
                    'fields': ['pos_qty'],
                    'ids': products.ids,
                }
            })

class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_stock_by_location(self, product_ids):
        config = self.config_id

        if config.show_stock_of == 'current_session':
            if config.stock_location_id:
                location_id = config.stock_location_id.id
            else:
                location_id = config.picking_type_id.default_location_src_id.id

            locations = self.env['stock.location'].search([
                ('id', 'child_of', location_id),
                ('usage', '=', 'internal'),
            ])

            quants = self.env['stock.quant'].search([
                ('product_id.product_tmpl_id', 'in', product_ids),
                ('location_id', 'in', locations.ids),
            ])
        else:

            quants = self.env['stock.quant'].search([
                ('product_id.product_tmpl_id', 'in', product_ids),
                ('location_id.usage', '=', 'internal'),
            ])

        result = {}
        for q in quants:
            tmpl_id = q.product_id.product_tmpl_id.id
            if tmpl_id not in result:
                result[tmpl_id] = []
            result[tmpl_id].append({
                'location': q.location_id.complete_name,
                'qty': q.quantity,
            })
        return result