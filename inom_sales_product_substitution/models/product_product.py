# -*- coding: utf-8 -*-
from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError

# Context key used to short-circuit the reciprocal synchronization while it is
# writing the reverse links, so the propagation does not recurse indefinitely.
SKIP_SYNC = "inom_skip_alternative_sync"


class ProductProduct(models.Model):
    _inherit = "product.product"

    inom_alternative_product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="inom_product_alternative_rel",
        column1="product_id",
        column2="alt_product_id",
        string="Alternative Products",
        domain="[('id', '!=', id)]",
        help="Products proposed as substitutes for this product when it is "
             "unavailable or low on stock. Links are kept symmetric "
             "automatically: adding an alternative here adds this product to "
             "that alternative in return, and every product in the group "
             "references each other.",
    )
    inom_show_alternative_products = fields.Boolean(
        string="Show Alternative Products",
        compute="_compute_inom_show_alternative_products",
        help="Technical field driven by the 'Manage Alternative Products' "
             "configuration setting. It controls the visibility of the "
             "Alternatives section on the product form.",
    )
    inom_alternative_product_count = fields.Integer(
        string="Alternative Products Count",
        compute="_compute_inom_alternative_product_count",
        help="Number of alternative products linked to this product. Used by "
             "the Alternatives smart button.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    def _compute_inom_show_alternative_products(self):
        enabled = self.env["ir.config_parameter"].sudo().get_param(
            "inom_sales_product_substitution.manage_alternative_products"
        )
        is_enabled = enabled in ("True", "true", "1", 1, True)
        for product in self:
            product.inom_show_alternative_products = is_enabled

    @api.depends("inom_alternative_product_ids")
    def _compute_inom_alternative_product_count(self):
        for product in self:
            product.inom_alternative_product_count = len(
                product.inom_alternative_product_ids
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_inom_view_alternatives(self):
        """Open the alternative products linked to this product."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Alternative Products",
            "res_model": "product.product",
            "view_mode": "list,form",
            "domain": [("id", "in", self.inom_alternative_product_ids.ids)],
            "context": {"create": False},
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Effective alternatives (variant-aware with template fallback)
    # ------------------------------------------------------------------
    def _inom_get_effective_alternatives(self):
        """Return the effective alternative products for this variant.

        Alternatives are stored on the variant (product.product). When the
        selected variant has its own alternatives, those are used. Otherwise
        the method falls back to the union of alternatives configured on any
        variant of the same product template. This handles multi-variant
        templates (for example the demo "Customizable Desk") where the variant
        sold on a sales order may differ from the variant on which alternatives
        were configured. The variant itself is always excluded.
        """
        self.ensure_one()
        alternatives = self.inom_alternative_product_ids
        if not alternatives:
            alternatives = self.product_tmpl_id.product_variant_ids.\
                inom_alternative_product_ids
        return alternatives - self

    # ------------------------------------------------------------------
    # Reciprocal synchronization helpers
    # ------------------------------------------------------------------
    def _inom_sync_added_alternatives(self):
        """Make each product and its alternatives a mutual group.

        Additive only. For every product, the group is defined as the product
        itself plus its current alternatives; each member of the group is then
        linked to every other member it does not yet reference. This keeps the
        relation symmetric and turns the group into a mutual set ("vice versa").
        """
        if self.env.context.get(SKIP_SYNC):
            return
        for product in self:
            group = product.inom_alternative_product_ids | product
            for member in group:
                missing = (group - member) - member.inom_alternative_product_ids
                if missing:
                    member.with_context(**{SKIP_SYNC: True}).write({
                        "inom_alternative_product_ids": [
                            Command.link(other.id) for other in missing
                        ]
                    })

    def _inom_sync_removed_alternatives(self, removed_by_product):
        """Remove the reverse link when an alternative is unlinked.

        :param removed_by_product: dict mapping a product id to the recordset
            of alternatives that were removed from it.
        """
        if self.env.context.get(SKIP_SYNC):
            return
        for product in self:
            removed = removed_by_product.get(product.id)
            if not removed:
                continue
            for other in removed:
                if product in other.inom_alternative_product_ids:
                    other.with_context(**{SKIP_SYNC: True}).write({
                        "inom_alternative_product_ids": [
                            Command.unlink(product.id)
                        ]
                    })

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products.filtered(
            "inom_alternative_product_ids"
        )._inom_sync_added_alternatives()
        return products

    def write(self, vals):
        if "inom_alternative_product_ids" not in vals or self.env.context.get(
            SKIP_SYNC
        ):
            return super().write(vals)

        before = {
            product.id: product.inom_alternative_product_ids for product in self
        }
        result = super().write(vals)

        removed_by_product = {}
        for product in self:
            removed = before[product.id] - product.inom_alternative_product_ids
            if removed:
                removed_by_product[product.id] = removed

        if removed_by_product:
            self._inom_sync_removed_alternatives(removed_by_product)
        self._inom_sync_added_alternatives()
        return result

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("inom_alternative_product_ids")
    def _check_inom_alternative_products(self):
        for product in self:
            if product in product.inom_alternative_product_ids:
                raise ValidationError(
                    "A product cannot be set as an alternative of itself."
                )
            if product.type == "combo" and product.inom_alternative_product_ids:
                raise ValidationError(
                    "Alternative products are not supported for products of "
                    "type 'Combo'."
                )
