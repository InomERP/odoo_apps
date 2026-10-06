# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InomProductSubstitutionHistory(models.Model):
    _name = "inom.product.substitution.history"
    _description = "Product Substitution History"
    _order = "replacement_date desc, id desc"

    order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
        required=True,
        ondelete="cascade",
        index=True,
        help="Sales order on which the substitution was performed.",
    )
    order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order Line",
        ondelete="set null",
        index=True,
        help="Sales order line whose product was replaced. Kept for audit "
             "even if the line is later removed.",
    )
    original_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Original Product",
        required=True,
        ondelete="restrict",
        help="Product that was on the line before the replacement.",
    )
    replacement_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Replacement Product",
        required=True,
        ondelete="restrict",
        help="Product that replaced the original product on the line.",
    )
    product_uom_qty = fields.Float(
        string="Quantity",
        help="Ordered quantity preserved during the replacement.",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Performed By",
        required=True,
        default=lambda self: self.env.user,
        index=True,
        help="User who performed the replacement.",
    )
    replacement_date = fields.Datetime(
        string="Date",
        required=True,
        default=fields.Datetime.now,
        help="Date and time at which the replacement was performed.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Company that owns the sales order.",
    )

    @api.depends("order_id", "original_product_id", "replacement_product_id")
    def _compute_display_name(self):
        for record in self:
            record.display_name = "%s: %s -> %s" % (
                record.order_id.name or "",
                record.original_product_id.display_name or "",
                record.replacement_product_id.display_name or "",
            )
