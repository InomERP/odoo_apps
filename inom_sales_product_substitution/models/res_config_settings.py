# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    inom_manage_alternative_products = fields.Boolean(
        string="Manage Alternative Products",
        config_parameter="inom_sales_product_substitution.manage_alternative_products",
        help="Enable management of alternative (substitute) products. When "
             "enabled, the Alternatives section becomes available on product "
             "variants.",
    )
