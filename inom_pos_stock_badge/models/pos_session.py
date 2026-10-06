# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_stock_by_location(self, product_ids):
        """ Return {template_id: [{'location', 'qty'}]} for the location popup of the badge. """
        self.ensure_one()
        config = self.config_id
        domain = [
            ('product_id.product_tmpl_id', 'in', product_ids),
            ('location_id.usage', '=', 'internal'),
            ('company_id', '=', config.company_id.id),
        ]
        location = config._get_inom_stock_location()
        if location:
            domain.append(('location_id', 'child_of', location.id))

        groups = self.env['stock.quant'].with_company(config.company_id)._read_group(
            domain,
            groupby=['product_id', 'location_id'],
            aggregates=['quantity:sum', 'reserved_quantity:sum'],
        )
        per_location = {}
        for product, location, quantity, reserved in groups:
            if config.stock_type == 'available':
                quantity -= reserved
            key = (product.product_tmpl_id.id, location.id)
            if key not in per_location:
                per_location[key] = {'location': location.complete_name, 'qty': 0.0}
            per_location[key]['qty'] += quantity

        result = {}
        for (tmpl_id, _location_id), vals in per_location.items():
            result.setdefault(tmpl_id, []).append(vals)
        for vals in result.values():
            vals.sort(key=lambda v: v['location'])
        return result
