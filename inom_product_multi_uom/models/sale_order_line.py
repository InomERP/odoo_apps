# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    """Secondary UoM handling on sale order lines (F-06 to F-09, F-11, F-12).

    The "Secondary UoM" is a real Unit of Measure (uom.uom). It defaults to:
      * the product's first-created secondary UoM, when the product defines
        secondary UoMs, or
      * the product's base UoM (e.g. Units), when it does not.
    The base ordered quantity is derived as secondary_qty x ratio, where the
    ratio comes from the matching product.secondary.uom (1.0 for the base
    UoM). All values are dynamic; nothing is hard-coded.
    """

    _inherit = "sale.order.line"

    # --- Stored related helpers (reliable list-row modifier evaluation) ---
    need_secondary_uom = fields.Boolean(
        related="product_id.product_tmpl_id.need_secondary_uom",
        string="Needs Secondary UoM",
        store=True,
    )
    inom_product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        related="product_id.product_tmpl_id",
        string="Product Template",
        store=True,
    )

    # Allowed secondary units = product base UoM + its configured secondary UoMs.
    inom_allowed_secondary_uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        compute="_compute_inom_allowed_secondary_uom_ids",
        string="Allowed Secondary UoMs",
    )

    # --- User inputs ---
    secondary_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Secondary UoM",
        domain="[('id', 'in', inom_allowed_secondary_uom_ids)]",
        help="Unit of Measure used for the secondary quantity. Defaults to "
             "the product's first secondary UoM, or to the base UoM when the "
             "product has no secondary UoM.",
    )
    secondary_qty = fields.Float(
        string="Secondary Qty",
        default=0.0,
        digits="Product Unit of Measure",
        help="Quantity expressed in the secondary UoM.",
    )

    # --- Dynamic, read-only display values ---
    secondary_factor = fields.Float(
        string="Conversion Ratio",
        compute="_compute_secondary_factor",
        help="Base units per 1 secondary unit for the selected UoM.",
    )
    base_uom_name = fields.Char(
        string="Base UoM",
        compute="_compute_inom_secondary_display",
    )
    secondary_conversion_display = fields.Char(
        string="Conversion",
        compute="_compute_inom_secondary_display",
        help="Human-readable conversion, e.g. '1 Dozones = 12 Units'.",
    )

    @api.depends("product_id")
    def _compute_inom_allowed_secondary_uom_ids(self):
        for line in self:
            tmpl = line.product_id.product_tmpl_id
            uoms = tmpl.secondary_uom_ids.mapped("uom_id")
            if tmpl.uom_id:
                uoms |= tmpl.uom_id
            line.inom_allowed_secondary_uom_ids = uoms

    def _inom_get_secondary_ratio(self):
        """Return base units per 1 secondary unit for the chosen UoM.

        The base UoM (or an unset UoM) converts 1:1; a configured secondary
        UoM uses the ratio stored on its product.secondary.uom line.
        """
        self.ensure_one()
        tmpl = self.product_id.product_tmpl_id
        if not self.secondary_uom_id or self.secondary_uom_id == tmpl.uom_id:
            return 1.0
        sec = tmpl.secondary_uom_ids.filtered(
            lambda s: s.uom_id == self.secondary_uom_id
        )[:1]
        return sec.ratio if sec else 1.0

    @api.depends("secondary_uom_id", "product_id")
    def _compute_secondary_factor(self):
        for line in self:
            line.secondary_factor = line._inom_get_secondary_ratio()

    @api.depends("secondary_uom_id", "secondary_qty", "product_id")
    def _compute_inom_secondary_display(self):
        for line in self:
            base_uom = line.product_id.product_tmpl_id.uom_id
            base_name = base_uom.name or ""
            line.base_uom_name = base_name
            if line.secondary_uom_id and line.secondary_qty:
                converted = line.secondary_qty * line._inom_get_secondary_ratio()
                line.secondary_conversion_display = "%s %s = %s %s" % (
                    ("%g" % line.secondary_qty),
                    line.secondary_uom_id.name or "",
                    ("%g" % converted),
                    base_name,
                )
            else:
                line.secondary_conversion_display = ""

    def _inom_apply_secondary_conversion(self):
        """F-07: base ordered qty = secondary qty x ratio (only for a real,
        non-base secondary UoM with a quantity)."""
        for line in self:
            tmpl = line.product_id.product_tmpl_id
            if (
                line.secondary_uom_id
                and line.secondary_uom_id != tmpl.uom_id
                and line.secondary_qty
            ):
                new_qty = line.secondary_qty * line._inom_get_secondary_ratio()
                if line.product_uom_qty != new_qty:
                    line.product_uom_qty = new_qty

    @api.onchange("secondary_uom_id", "secondary_qty")
    def _onchange_inom_secondary_uom(self):
        self._inom_apply_secondary_conversion()

    @api.onchange("product_id")
    def _onchange_inom_product_set_secondary(self):
        """Default the Secondary UoM dynamically:

        - product with secondary UoMs -> first-created secondary unit,
        - product without secondary UoMs -> the base unit (e.g. Units).
        The secondary quantity is left at zero, so the base ordered quantity
        is unchanged until the user enters a secondary quantity.
        """
        for line in self:
            tmpl = line.product_id.product_tmpl_id
            if tmpl.need_secondary_uom and tmpl.secondary_uom_ids:
                first_secondary = tmpl.secondary_uom_ids.sorted("id")[:1]
                line.secondary_uom_id = first_secondary.uom_id
            elif tmpl.uom_id:
                line.secondary_uom_id = tmpl.uom_id
                line.secondary_qty = 0.0
            else:
                line.secondary_uom_id = False
                line.secondary_qty = 0.0

    # ------------------------------------------------------------------
    # F-12: Validation
    # ------------------------------------------------------------------
    @api.constrains("secondary_uom_id", "product_id")
    def _check_secondary_uom_matches_product(self):
        """The chosen secondary UoM must be the base UoM or one of the
        product's configured secondary UoMs."""
        for line in self:
            if not line.secondary_uom_id or not line.product_id:
                continue
            tmpl = line.product_id.product_tmpl_id
            allowed = tmpl.secondary_uom_ids.mapped("uom_id")
            if tmpl.uom_id:
                allowed |= tmpl.uom_id
            if line.secondary_uom_id not in allowed:
                raise ValidationError(
                    _("The selected secondary UoM is not valid for the "
                      "product '%s'.") % line.product_id.display_name
                )

    # ------------------------------------------------------------------
    # F-11: Invoice synchronisation
    # ------------------------------------------------------------------
    def _prepare_invoice_line(self, **optional_values):
        """Carry a real (non-base) secondary UoM reference to the invoice
        line. The invoice quantity itself stays the correct base quantity."""
        res = super()._prepare_invoice_line(**optional_values)
        tmpl = self.product_id.product_tmpl_id
        if self.secondary_uom_id and self.secondary_uom_id != tmpl.uom_id:
            res.update(
                {
                    "secondary_uom_id": self.secondary_uom_id.id,
                    "secondary_qty": self.secondary_qty,
                }
            )
        return res

    def _inom_default_secondary_uom(self, product_id):
        """Return the uom.uom id that should default into secondary_uom_id
        for the given product (first secondary UoM, else base UoM)."""
        if not product_id:
            return False
        tmpl = self.env["product.product"].browse(product_id).product_tmpl_id
        if tmpl.need_secondary_uom and tmpl.secondary_uom_ids:
            return tmpl.secondary_uom_ids.sorted("id")[:1].uom_id.id
        if tmpl.uom_id:
            return tmpl.uom_id.id
        return False

    @api.model_create_multi
    def create(self, vals_list):
        # The Secondary UoM field is read-only for products without secondary
        # UoMs, so its onchange value is not submitted by the client. Set the
        # default here so the shown UoM (e.g. Units) persists after saving.
        for vals in vals_list:
            if not vals.get("secondary_uom_id") and vals.get("product_id"):
                default_uom = self._inom_default_secondary_uom(vals["product_id"])
                if default_uom:
                    vals["secondary_uom_id"] = default_uom
        lines = super().create(vals_list)
        lines._inom_apply_secondary_conversion()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if {"secondary_qty", "secondary_uom_id"} & set(vals):
            self._inom_apply_secondary_conversion()
        # When the product changes but the (read-only) Secondary UoM is not
        # submitted, refresh it server-side so it persists.
        if "product_id" in vals and "secondary_uom_id" not in vals:
            for line in self:
                if not line.secondary_uom_id:
                    default_uom = line._inom_default_secondary_uom(
                        line.product_id.id
                    )
                    if default_uom:
                        line.secondary_uom_id = default_uom
        return res
