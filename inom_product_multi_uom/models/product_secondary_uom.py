# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductSecondaryUom(models.Model):
    """A secondary Unit of Measure defined for a product template.

    Each line links a product to one uom.uom and stores a conversion
    ratio expressed as: 1 secondary unit = ratio base units.
    """

    _name = "product.secondary.uom"
    _description = "Product Secondary Unit of Measure"
    _rec_name = "uom_id"

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Secondary UoM",
        required=True,
        help="The secondary Unit of Measure available for this product.",
    )
    ratio = fields.Float(
        string="Ratio",
        default=1.0,
        digits="Product Unit of Measure",
        help="Conversion ratio: 1 secondary unit = ratio base units.",
    )
    ratio_display = fields.Char(
        string="Ratio",
        compute="_compute_ratio_display",
        help="Human-readable ratio: e.g. 1 Dozen = 12.0 Units",
    )

    @api.depends("uom_id", "ratio", "product_tmpl_id.uom_id")
    def _compute_ratio_display(self):
        for rec in self:
            base_uom = rec.product_tmpl_id.uom_id.name or ""
            uom_name = rec.uom_id.name or ""
            rec.ratio_display = f"1 {uom_name} = {rec.ratio} {base_uom}"

    _sql_constraints = [
        (
            "ratio_strictly_positive",
            "CHECK(ratio > 0)",
            "The ratio to the base UoM must be strictly greater than zero.",
        ),
    ]

    # ------------------------------------------------------------------
    # F-12: Secondary UoM validation
    # ------------------------------------------------------------------
    @api.constrains("ratio")
    def _check_ratio_positive(self):
        for rec in self:
            if rec.ratio <= 0:
                raise ValidationError(
                    _("The ratio to the base UoM must be strictly greater "
                      "than zero.")
                )

    @api.constrains("uom_id", "product_tmpl_id")
    def _check_secondary_uom_valid(self):
        """Reject incompatible / duplicate secondary UoMs (F-12).

        - The same UoM may not be defined twice for one product.
        - A secondary UoM must differ from the product's base UoM, since an
          identical 1:1 line carries no conversion value.
        """
        for rec in self:
            if not rec.uom_id or not rec.product_tmpl_id:
                continue
            base_uom = rec.product_tmpl_id.uom_id
            if base_uom and rec.uom_id == base_uom:
                raise ValidationError(
                    _("The secondary UoM cannot be the same as the product's "
                      "base UoM '%s'.") % base_uom.name
                )
            duplicate = self.search_count(
                [
                    ("product_tmpl_id", "=", rec.product_tmpl_id.id),
                    ("uom_id", "=", rec.uom_id.id),
                    ("id", "!=", rec.id),
                ]
            )
            if duplicate:
                raise ValidationError(
                    _("The secondary UoM '%s' is already defined for this "
                      "product.") % rec.uom_id.name
                )
