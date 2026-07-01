# -*- coding: utf-8 -*-
from odoo import models, api


class SaleCostDownReport(models.AbstractModel):
    _name = "report.inom_smart_price_history.report_sale_cost_down_template"
    _description = "Quotation Cost Down Report"

    @api.model
    def _get_cost_down_lines(self, order):
        """Build the per-product cost-down rows for one sale order.

        Original price = the oldest logged old_price for that order line if
        any revision was logged, otherwise the current unit price (no
        revisions means no cost-down).
        Revised price = current unit price on the order line.
        """
        lines = []
        for order_line in order.order_line.filtered(lambda l: l.product_id):
            logs = self.env["inom.sale.price.log"].search(
                [("order_line_id", "=", order_line.id)],
                order="change_date asc",
            )
            original_price = logs[0].old_price if logs else order_line.price_unit
            revised_price = order_line.price_unit
            cost_down_percent = 0.0
            if original_price:
                cost_down_percent = (
                    (original_price - revised_price) / original_price
                ) * 100.0
            lines.append({
                "product": order_line.product_id.display_name,
                "original_price": original_price,
                "revised_price": revised_price,
                "cost_down_percent": cost_down_percent,
                "currency": order.currency_id,
                "revision_count": len(logs),
            })
        return lines

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["sale.order"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "sale.order",
            "docs": docs,
            "get_cost_down_lines": self._get_cost_down_lines,
        }
