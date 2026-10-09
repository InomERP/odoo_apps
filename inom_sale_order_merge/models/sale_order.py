# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    """Phase 5/6: consolidate duplicate order lines on a single sale order.

    This is independent from the Phase 1-4 wizards (which merge *different*
    orders into one and never touch line content). Here we merge *lines
    within the same order* that share the same product/price/discount/tax,
    summing their quantity onto a single line.
    """
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Core line-merge logic (reused by the manual wizard and by auto-merge)
    # ------------------------------------------------------------------
    def _get_merge_line_key(self, line):
        """Key used to detect duplicate lines. Lines only merge when the
        product, unit of measure, unit price, discount and taxes all match -
        this mirrors the target screenshots, where a line with a different
        price for the same product is intentionally kept separate.
        """
        return (
            line.product_id.id,
            line.product_uom_id.id,
            line.price_unit,
            line.discount,
            tuple(sorted(line.tax_ids.ids)),
        )

    def _merge_duplicate_order_lines(self):
        """Merge order lines that share the same key onto a single line by
        summing their ordered quantity. Section/note lines (and any line
        without a product) are never touched.
        """
        SaleOrderLine = self.env['sale.order.line']
        for order in self:
            groups = {}
            for line in order.order_line:
                if line.display_type or not line.product_id:
                    continue
                key = order._get_merge_line_key(line)
                groups.setdefault(key, SaleOrderLine)
                groups[key] |= line

            lines_to_unlink = SaleOrderLine
            for lines in groups.values():
                if len(lines) < 2:
                    continue
                keep_line = lines[0]
                duplicate_lines = lines[1:]
                keep_line.product_uom_qty = sum(lines.mapped('product_uom_qty'))
                lines_to_unlink |= duplicate_lines

            if lines_to_unlink:
                lines_to_unlink.unlink()
        return True

    def action_merge_order_lines(self):
        """Entry point used by the 'Merge Order Lines' confirmation wizard."""
        self.ensure_one()
        self._merge_duplicate_order_lines()
        return True

    # ------------------------------------------------------------------
    # Auto-merge on create/write (Phase 6 settings toggle)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        auto_orders = orders.filtered(lambda o: o.company_id.auto_merge_sale_order_lines)
        if auto_orders:
            auto_orders._merge_duplicate_order_lines()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'order_line' in vals:
            auto_orders = self.filtered(lambda o: o.company_id.auto_merge_sale_order_lines)
            if auto_orders:
                auto_orders._merge_duplicate_order_lines()
        return res
