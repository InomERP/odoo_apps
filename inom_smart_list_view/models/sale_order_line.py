# -*- coding: utf-8 -*-
from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    order_line_image = fields.Image(
        string="Product Image",
        related='product_id.image_1920',
        store=False,
        help="Image of the ordered product, taken from the product record.",
    )
    contact_email = fields.Char(
        string="Customer Email",
        related='order_partner_id.email',
        store=False,
        help="Email of the customer, taken from the order's customer.",
    )
    contact_phone = fields.Char(
        string="Customer Phone",
        related='order_partner_id.phone',
        store=False,
        help="Phone of the customer, taken from the order's customer.",
    )
