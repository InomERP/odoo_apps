# -*- coding: utf-8 -*-
from odoo import api, models


class PosOrderLine(models.Model):
    """
    Extend pos.order.line so the frontend gets `pack_lot_ids`
    (the standard M2O field linking lines to pos.pack.operation.lot rows).
    """
    _inherit = 'pos.order.line'

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        fields_list = super()._load_pos_data_fields(*args, **kwargs)
        for f in ('pack_lot_ids',):
            if f not in fields_list:
                fields_list.append(f)
        return fields_list
