# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    """Extend the product template with secondary UoM configuration."""

    _inherit = "product.template"

    need_secondary_uom = fields.Boolean(
        string="Need Secondary UoMs",
        default=False,
        help="Enable to manage one or more secondary Units of Measure for this product.",
    )
    secondary_uom_ids = fields.One2many(
        comodel_name="product.secondary.uom",
        inverse_name="product_tmpl_id",
        string="Secondary UoMs",
    )

    def action_open_secondary_uom_wizard(self):
        """Open the Add Secondary UoM popup wizard for this product template."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Create Secondary UoM's",
            "res_model": "secondary.uom.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
            },
        }
