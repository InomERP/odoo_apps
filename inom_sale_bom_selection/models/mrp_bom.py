# -*- coding: utf-8 -*-
from odoo import api, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def _bom_find(self, products, picking_type=None, company_id=False, bom_type=False):
        """Allow forcing a specific Kit (phantom) BoM during explosion.

        When a stock move carries the context key ``inom_forced_kit_bom_id``
        (set by ``stock.move._action_explode``), and the standard lookup is for
        a phantom BoM, this method substitutes the forced Kit BoM for the
        matching products. For every other case the native behaviour is kept.
        """
        result = super()._bom_find(
            products,
            picking_type=picking_type,
            company_id=company_id,
            bom_type=bom_type,
        )
        forced_bom_id = self.env.context.get('inom_forced_kit_bom_id')
        if not forced_bom_id or bom_type != 'phantom':
            return result
        forced_bom = self.browse(forced_bom_id).exists()
        if not forced_bom or forced_bom.type != 'phantom':
            return result
        for product in products:
            if forced_bom.product_id:
                matches = forced_bom.product_id == product
            else:
                matches = forced_bom.product_tmpl_id == product.product_tmpl_id
            if matches:
                result[product] = forced_bom
        return result
