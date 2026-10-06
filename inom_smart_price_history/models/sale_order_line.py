# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def action_view_invoice_price_history(self):
        """F-01: Open the invoice price history wizard for the product on this
        sale order line, scoped to the customer of the related sale order.
        """
        self.ensure_one()
        if not self.product_id:
            raise UserError(_("Please select a product on this line first."))
        partner = self.order_id.partner_id
        if not partner:
            raise UserError(_("Please set a customer on the order first."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoice Price History"),
            "res_model": "invoice.history.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_product_id": self.product_id.id,
                "default_partner_id": partner.id,
            },
        }

    def write(self, vals):
        """F-10: Track unit price revisions on sale order lines, and keep
        the product's Sales Price (list_price) in sync with the latest
        sale price.
        """
        track = "price_unit" in vals
        old_prices = {}
        if track:
            for line in self:
                if line.product_id:
                    old_prices[line.id] = line.price_unit
        res = super().write(vals)
        if track and old_prices:
            log_model = self.env["inom.sale.price.log"]
            for line in self:
                old_price = old_prices.get(line.id)
                if old_price is None or not line.product_id:
                    continue
                currency = line.currency_id or line.order_id.currency_id
                rounding = (currency or line.company_id.currency_id).rounding
                if float_compare(line.price_unit, old_price,
                                 precision_rounding=rounding) == 0:
                    continue
                log_model.log_price_change(
                    order_line=line,
                    old_price=old_price,
                    new_price=line.price_unit,
                )
                line.product_id.product_tmpl_id.write(
                    {"list_price": line.price_unit}
                )
        return res
