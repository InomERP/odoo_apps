# -*- coding: utf-8 -*-
from odoo import models, fields


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data_models(self, config_id):
        models_list = super()._load_pos_data_models(config_id)
        if 'stock.location' not in models_list:
            models_list.append('stock.location')
        return models_list

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


class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = ['stock.location', 'pos.load.mixin']

    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'complete_name', 'usage', 'location_id']

    def _load_pos_data_domain(self, data):
        return [('usage', '=', 'internal')]
