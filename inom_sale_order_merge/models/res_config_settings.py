# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_merge_sale_order_lines = fields.Boolean(
        related='company_id.auto_merge_sale_order_lines',
        readonly=False,
        string='Auto Merge Sale Order Lines',
        help="Will automatically merge sale order lines while creating or "
             "editing an order.",
    )
