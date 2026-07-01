# -*- coding: utf-8 -*-
from odoo import models, fields, api


class InomSalePriceLog(models.Model):
    _name = "inom.sale.price.log"
    _description = "Sale Order Line Price Change Log"
    _order = "change_date desc, id desc"
    _rec_name = "product_id"

    order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
        required=True,
        ondelete="cascade",
        index=True,
    )
    order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Order Line",
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    old_price = fields.Monetary(
        string="Old Price",
        currency_field="currency_id",
    )
    new_price = fields.Monetary(
        string="New Price",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
    )
    change_date = fields.Datetime(
        string="Changed On",
        default=fields.Datetime.now,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Changed By",
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    @api.model
    def log_price_change(self, order_line, old_price, new_price):
        """Centralised helper to record a single sale order line price change.

        Created with sudo() because the originating action (editing a sale
        order/quotation line) may be performed by a user who does not hold
        create rights on this internal audit model. The data written is
        strictly limited to the order line the user is already editing.
        """
        if not order_line or not order_line.product_id:
            return self.browse()
        order = order_line.order_id
        return self.sudo().create({
            "order_id": order.id,
            "order_line_id": order_line.id,
            "product_id": order_line.product_id.id,
            "old_price": old_price,
            "new_price": new_price,
            "currency_id": order.currency_id.id if order.currency_id else False,
            "company_id": order.company_id.id if order.company_id else self.env.company.id,
        })
