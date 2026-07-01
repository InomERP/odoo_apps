# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def action_view_bill_price_history(self):
        """F-03: Open the bill price history wizard for the product on this
        purchase order line, scoped to the vendor of the related purchase order.
        """
        self.ensure_one()
        if not self.product_id:
            raise UserError(_("Please select a product on this line first."))
        partner = self.order_id.partner_id
        if not partner:
            raise UserError(_("Please set a vendor on the order first."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Bill Price History"),
            "res_model": "bill.history.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_product_id": self.product_id.id,
                "default_partner_id": partner.id,
            },
        }

    def write(self, vals):
        """F-08: Track unit price revisions on purchase order lines, and
        keep the product's Cost (standard_price) in sync with the latest
        purchase price.
        """
        track = "price_unit" in vals
        old_prices = {}
        if track:
            for line in self:
                if line.product_id:
                    old_prices[line.id] = line.price_unit
        res = super().write(vals)
        if track and old_prices:
            log_model = self.env["inom.price.change.log"]
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
                    product=line.product_id,
                    source="purchase",
                    old_price=old_price,
                    new_price=line.price_unit,
                    currency=currency,
                    partner=line.order_id.partner_id,
                    purchase_order=line.order_id,
                    reference=line.order_id.name,
                    company=line.company_id,
                )
                line.product_id.with_context(
                    skip_price_log=True
                ).write({"standard_price": line.price_unit})
        return res
