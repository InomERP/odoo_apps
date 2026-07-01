# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import float_compare


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _inom_should_track_price(self):
        """Return True when this line is a product line on a customer invoice
        or vendor bill, and therefore eligible for price revision tracking
        (F-07 for invoices, F-08 for bills).
        """
        self.ensure_one()
        return bool(
            self.product_id
            and self.display_type == "product"
            and self.move_id.move_type in ("out_invoice", "in_invoice")
        )

    def write(self, vals):
        track = "price_unit" in vals
        old_prices = {}
        if track:
            for line in self:
                if line._inom_should_track_price():
                    old_prices[line.id] = line.price_unit
        res = super().write(vals)
        if track and old_prices:
            log_model = self.env["inom.price.change.log"]
            for line in self:
                old_price = old_prices.get(line.id)
                if old_price is None:
                    continue
                rounding = (line.currency_id or line.company_currency_id).rounding
                if float_compare(line.price_unit, old_price,
                                 precision_rounding=rounding) == 0:
                    continue
                if not line._inom_should_track_price():
                    continue
                log_model.log_price_change(
                    product=line.product_id,
                    source="invoice" if line.move_id.move_type == "out_invoice" else "bill",
                    old_price=old_price,
                    new_price=line.price_unit,
                    currency=line.currency_id,
                    partner=line.move_id.partner_id,
                    move=line.move_id,
                    reference=line.move_id.name or line.move_id.ref,
                    company=line.company_id,
                )
                # Keep the product pricing in sync: customer invoices feed
                # the Sales Price, vendor bills feed the Cost.
                if line.move_id.move_type == "out_invoice":
                    line.product_id.product_tmpl_id.write(
                        {"list_price": line.price_unit}
                    )
                elif line.move_id.move_type == "in_invoice":
                    line.product_id.write({"standard_price": line.price_unit})
        return res