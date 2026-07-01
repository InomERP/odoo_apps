# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.tools import float_compare


class ProductProduct(models.Model):
    _inherit = "product.product"

    price_change_log_ids = fields.One2many(
        comodel_name="inom.price.change.log",
        inverse_name="product_id",
        string="Price Change Log",
    )

    def write(self, vals):
        track = "standard_price" in vals
        old_costs = {}
        if track:
            for product in self:
                old_costs[product.id] = product.standard_price
        res = super().write(vals)
        if track and old_costs:
            log_model = self.env["inom.price.change.log"]
            company = self.env.company
            for product in self:
                old_cost = old_costs.get(product.id)
                if old_cost is None:
                    continue
                new_cost = product.standard_price
                rounding = company.currency_id.rounding
                if float_compare(new_cost, old_cost,
                                 precision_rounding=rounding) == 0:
                    continue
                log_model.log_price_change(
                    product=product,
                    source="cost",
                    old_price=old_cost,
                    new_price=new_cost,
                    currency=company.currency_id,
                    reference=company.name,
                    company=company,
                )
        return res
