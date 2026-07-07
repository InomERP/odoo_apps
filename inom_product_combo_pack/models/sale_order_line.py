# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    pack_id = fields.Many2one(
        comodel_name='product.template',
        string='Combo Pack',
        help='The combo pack this line belongs to.',
    )
    is_pack_parent = fields.Boolean(string='Is Pack Parent Line')
    is_pack_component = fields.Boolean(string='Is Pack Component Line')

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        # Parent pack lines only carry the price and display of the pack. The
        # delivery of a pack is produced by its component lines, so the parent
        # line must not generate its own stock move.
        deliverable_lines = self.filtered(lambda line: not line.is_pack_parent)
        return super(
            SaleOrderLine, deliverable_lines
        )._action_launch_stock_rule(
            previous_product_uom_qty=previous_product_uom_qty
        )
