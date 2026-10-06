# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    price_history_ids = fields.One2many(
        comodel_name="inom.sale.price.log",
        inverse_name="order_id",
        string="Price History",
    )
