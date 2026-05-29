# -*- coding: utf-8 -*-
from odoo import api, models


class PosOrder(models.Model):
    """
    Light extension to pos.order.
    The lot data itself lives at the order-line level; this class
    only needs to ensure data-loading consistency. Receipt-printing
    logic is wired in Phase 6.
    """
    _inherit = 'pos.order'

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        fields_list = super()._load_pos_data_fields(*args, **kwargs)
        # Currently nothing extra to load at the header level.
        # Reserved here for future config-driven enhancements
        # (e.g., per-order lot validation report).
        return fields_list
