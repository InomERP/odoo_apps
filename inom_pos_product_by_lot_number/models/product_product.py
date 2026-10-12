# -*- coding: utf-8 -*-
from odoo import api, models


class ProductProduct(models.Model):
    """
    Expose `tracking` to the POS frontend so the UI can dynamically
    branch on 'none', 'lot' or 'serial' without an extra RPC call.
    """
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        fields_list = super()._load_pos_data_fields(*args, **kwargs)
        for f in ('tracking',):
            if f not in fields_list:
                fields_list.append(f)
        return fields_list
