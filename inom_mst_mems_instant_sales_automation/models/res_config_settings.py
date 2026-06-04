# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # =========================================================
    # INSTANT SALE SEQUENCE PREFIX
    # =========================================================

    instant_sale_sequence_prefix = fields.Char(
        string='Instant Sale Sequence Prefix',
        default='IN/SO',
        config_parameter='mst_instant_sale.sequence_prefix',
    )

    # =========================================================
    # AUTO VALIDATE DELIVERY
    # =========================================================

    auto_validate_delivery = fields.Boolean(
        string='Auto Validate Delivery',
        default=True,
        config_parameter='mst_instant_sale.auto_validate_delivery',
        help='''
Automatically validates delivery orders
when confirming instant sale orders.
'''
    )

    # =========================================================
    # AUTO CREATE INVOICE
    # =========================================================

    auto_create_invoice = fields.Boolean(
        string='Auto Create Invoice',
        default=True,
        config_parameter='mst_instant_sale.auto_create_invoice',
        help='''
Automatically creates invoice
after confirming instant sale order.
'''
    )

    # =========================================================
    # AUTO POST INVOICE
    # =========================================================

    auto_post_invoice = fields.Boolean(
        string='Auto Post Invoice',
        default=True,
        config_parameter='mst_instant_sale.auto_post_invoice',
        help='''
Automatically posts invoices
after invoice creation.
'''
    )

    # =========================================================
    # AUTO REGISTER PAYMENT
    # =========================================================

    auto_register_payment = fields.Boolean(
        string='Auto Register Payment',
        default=True,
        config_parameter='mst_instant_sale.auto_register_payment',
        help='''
Automatically registers customer payment
after invoice posting.
'''
    )

    # =========================================================
    # AUTO RETURN DELIVERY ON CANCEL
    # =========================================================

    auto_return_delivery_on_cancel = fields.Boolean(
        string='Auto Return Delivery On Cancel',
        default=True,
        config_parameter='mst_instant_sale.auto_return_delivery_on_cancel',
        help='''
Automatically creates reverse transfer
when cancelling sale order.
'''
    )

    # =========================================================
    # AUTO CANCEL INVOICE ON CANCEL
    # =========================================================

    auto_cancel_invoice_on_cancel = fields.Boolean(
        string='Auto Cancel Invoice On Cancel',
        default=True,
        config_parameter='mst_instant_sale.auto_cancel_invoice_on_cancel',
        help='''
Automatically cancels invoice
when sale order is cancelled.
'''
    )

    # =========================================================
    # ALLOW NEGATIVE STOCK
    # =========================================================

    allow_negative_stock = fields.Boolean(
        string='Allow Negative Stock',
        default=False,
        config_parameter='mst_instant_sale.allow_negative_stock',
        help='''
Allows validating delivery
even if stock is unavailable.
'''
    )

    # =========================================================
    # ALLOW PARTIAL DELIVERY
    # =========================================================

    allow_partial_delivery = fields.Boolean(
        string='Allow Partial Delivery',
        default=True,
        config_parameter='mst_instant_sale.allow_partial_delivery',
        help='''
Allows partial delivery
when full quantity is not available.
'''
    )