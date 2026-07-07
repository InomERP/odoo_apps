# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    pack_id = fields.Many2one(
        comodel_name='product.template',
        string='Combo Pack',
        help='The combo pack this line belongs to.',
    )
    is_pack_parent = fields.Boolean(string='Is Pack Parent Line')
    is_pack_component = fields.Boolean(string='Is Pack Component Line')

    def _create_stock_moves(self, picking):
        # Parent pack lines only carry the cost and display of the pack. The
        # receipt of a pack is produced by its component lines, so the parent
        # line must not generate its own stock move.
        receivable_lines = self.filtered(lambda line: not line.is_pack_parent)
        return super(
            PurchaseOrderLine, receivable_lines
        )._create_stock_moves(picking)
