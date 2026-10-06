# -*- coding: utf-8 -*-
from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(
        self, product_id, product_qty, product_uom, location_dest_id,
        name, origin, company_id, values, bom
    ):
        """Carry the originating Sale Order Line onto the Odoo 20 MO.

        Odoo 20 passes sale_line_id in procurement values but no longer stores
        it directly on mrp.production. The module stores it in its own field
        so the v19 duplicate-prevention behaviour is retained.
        """
        vals = super()._prepare_mo_vals(
            product_id, product_qty, product_uom, location_dest_id,
            name, origin, company_id, values, bom
        )
        sale_line = values.get('sale_line_id')
        if sale_line:
            vals['inom_sale_line_id'] = (
                sale_line.id if hasattr(sale_line, 'id') else sale_line
            )
        return vals
