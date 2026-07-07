# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_pack_on_purchase = fields.Boolean(
        string='Allow Combo Pack on Purchase',
        config_parameter='inom_product_combo_pack.allow_pack_on_purchase',
        help='Allow adding combo packs on purchase orders.',
    )
