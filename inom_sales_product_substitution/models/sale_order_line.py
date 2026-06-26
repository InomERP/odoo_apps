# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

CONFIG_KEY = "inom_sales_product_substitution.manage_alternative_products"


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    inom_alternative_product_count = fields.Integer(
        string="Alternative Products Count",
        compute="_compute_inom_alternative_data",
        help="Number of alternative products linked to this line's product.",
    )
    inom_qty_available = fields.Float(
        string="Available Quantity",
        compute="_compute_inom_alternative_data",
        help="On-hand quantity of this line's product in the order warehouse "
             "(or company-wide when no warehouse is defined).",
    )
    inom_stock_insufficient = fields.Boolean(
        string="Insufficient Stock",
        compute="_compute_inom_alternative_data",
        help="True when the ordered quantity exceeds the available stock for a "
             "storable product.",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _inom_get_available_qty(self, product):
        """Return the on-hand quantity of a product in the order warehouse
        when one is defined, otherwise company-wide."""
        self.ensure_one()
        warehouse = getattr(self.order_id, "warehouse_id", False)
        if warehouse:
            product = product.with_context(warehouse_id=warehouse.id)
        return product.qty_available

    def _inom_alternatives_enabled(self):
        enabled = self.env["ir.config_parameter"].sudo().get_param(CONFIG_KEY)
        return enabled in ("True", "true", "1", 1, True)

    # ------------------------------------------------------------------
    # Allow a controlled in-place product replacement
    # ------------------------------------------------------------------
    def _compute_product_updatable(self):
        """Extend the native computation so that a product replacement driven
        by this module (under the 'inom_force_product_replace' context) can
        update the product in place, avoiding duplicate lines. This relaxes
        only the product-update guard and does not affect locked orders, which
        keep their own protection in sale.order.line.write()."""
        super()._compute_product_updatable()
        if self.env.context.get("inom_force_product_replace"):
            for line in self:
                line.product_updatable = True

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("product_id", "product_uom_qty")
    def _compute_inom_alternative_data(self):
        for line in self:
            product = line.product_id
            alternatives = product._inom_get_effective_alternatives() \
                if product else self.env["product.product"]
            count = len(alternatives)
            available = line._inom_get_available_qty(product) if product else 0.0
            insufficient = bool(
                product
                and product.type == "product"
                and line.product_uom_qty > available
            )
            line.inom_alternative_product_count = count
            line.inom_qty_available = available
            line.inom_stock_insufficient = insufficient

            # Temporary debug logging - remove once verified.
            _logger.info(
                "[INOM ALT DEBUG] line=%s product_id=%s (%s) tmpl=%s "
                "variant_own_count=%s effective_count=%s",
                line.id,
                product.id,
                product.display_name,
                product.product_tmpl_id.id if product else False,
                len(product.inom_alternative_product_ids) if product else 0,
                count,
            )

    # ------------------------------------------------------------------
    # Onchange suggestion
    # ------------------------------------------------------------------
    @api.onchange("product_id", "product_uom_qty")
    def _onchange_inom_suggest_alternatives(self):
        for line in self:
            if not line.product_id or not line._inom_alternatives_enabled():
                continue
            if (
                line.inom_stock_insufficient
                and line.inom_alternative_product_count
            ):
                return {
                    "warning": {
                        "title": "Insufficient Stock",
                        "message": (
                            "Only %(available)s unit(s) of '%(product)s' are "
                            "available, but %(requested)s were requested. "
                            "%(count)s alternative product(s) exist. Use the "
                            "'Alternatives' button on the line to review and "
                            "replace it."
                            % {
                                "available": line.inom_qty_available,
                                "product": line.product_id.display_name,
                                "requested": line.product_uom_qty,
                                "count": line.inom_alternative_product_count,
                            }
                        ),
                    }
                }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_inom_show_alternatives(self):
        """Open the alternative-product replacement wizard for this line."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Alternative Products",
            "res_model": "inom.alternative.product.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_order_line_id": self.id,
                "dialog_size": "xl",
            },
        }
