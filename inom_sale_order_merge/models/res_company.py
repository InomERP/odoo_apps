# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_merge_sale_order_lines = fields.Boolean(
        string='Auto Merge Sale Order Lines',
        help="When enabled, sale order lines for the same product/price/tax "
             "are automatically merged (quantities summed) whenever a sale "
             "order is created or its lines are edited.",
    )
