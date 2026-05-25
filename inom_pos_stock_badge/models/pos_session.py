# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):

        result = super()._loader_params_product_product()

        extra_fields = ['type']

        for f in extra_fields:
            if f not in result['search_params']['fields']:
                result['search_params']['fields'].append(f)

        return result

    def _get_pos_ui_product_product(self, params):

        products = super()._get_pos_ui_product_product(params)

        product_ids = [p['id'] for p in products]
        if not product_ids:
            return products

        config = self.config_id
        show_stock_of = config.show_stock_of or 'all_warehouse'

        # ------------------------------------------------------------------ #
        #  Determine location filter                                           #
        # ------------------------------------------------------------------ #
        domain_location = []

        if show_stock_of == 'current_session':
            location = config.stock_location_id
            if not location:
                location = config.picking_type_id.default_location_src_id

            if location:
                domain_location = [('location_id', 'child_of', location.id)]
            else:
                domain_location = [('location_id.usage', '=', 'internal')]
        else:
            domain_location = [('location_id.usage', '=', 'internal')]

        quants = self.env['stock.quant'].search(
            [('product_id', 'in', product_ids)] + domain_location
        )

        qty_map = {}
        for q in quants:
            pid = q.product_id.id
            if pid not in qty_map:
                qty_map[pid] = {'on_hand': 0.0, 'reserved': 0.0}
            qty_map[pid]['on_hand']   += q.quantity
            qty_map[pid]['reserved']  += q.reserved_quantity

        product_types = {
            rec.id: rec.type
            for rec in self.env['product.product'].browse(product_ids)
        }

        for product in products:
            pid  = product['id']
            data = qty_map.get(pid)

            if data:
                on_hand   = data['on_hand']
                reserved  = data['reserved']
                available = on_hand - reserved

                product['inom_stock_qty']      = on_hand
                product['inom_virtual_qty']    = available
            else:
                product.setdefault('inom_stock_qty',   0.0)
                product.setdefault('inom_virtual_qty', 0.0)

            product['type'] = product_types.get(pid, 'product')

        return products

    def get_stock_by_location(self, product_ids):
        """
        Location-wise stock popup.
        """
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