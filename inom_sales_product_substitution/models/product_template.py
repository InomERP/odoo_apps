# -*- coding: utf-8 -*-
from odoo import api, fields, models

CONFIG_KEY = "inom_sales_product_substitution.manage_alternative_products"


class ProductTemplate(models.Model):
    _inherit = "product.template"

    inom_show_alternative_products = fields.Boolean(
        string="Show Alternative Products",
        compute="_compute_inom_show_alternative_products",
        help="Technical field driven by the 'Manage Alternative Products' "
             "setting; controls visibility of alternative-related elements.",
    )
    inom_alternative_product_count = fields.Integer(
        string="Alternative Products Count",
        compute="_compute_inom_alternative_product_count",
        help="Total number of distinct alternative products across this "
             "product's variants. The source of truth remains the variant "
             "(product.product) field.",
    )

    def _compute_inom_show_alternative_products(self):
        enabled = self.env["ir.config_parameter"].sudo().get_param(CONFIG_KEY)
        is_enabled = enabled in ("True", "true", "1", 1, True)
        for template in self:
            template.inom_show_alternative_products = is_enabled

    @api.depends("product_variant_ids.inom_alternative_product_ids")
    def _compute_inom_alternative_product_count(self):
        for template in self:
            alternatives = template.product_variant_ids.\
                inom_alternative_product_ids
            template.inom_alternative_product_count = len(alternatives)

    def action_inom_view_alternatives(self):
        """Open the alternative products across all variants of this template."""
        self.ensure_one()
        alternatives = self.product_variant_ids.inom_alternative_product_ids
        return {
            "type": "ir.actions.act_window",
            "name": "Alternative Products",
            "res_model": "product.product",
            "view_mode": "list,form",
            "domain": [("id", "in", alternatives.ids)],
            "context": {"create": False},
            "target": "current",
        }
