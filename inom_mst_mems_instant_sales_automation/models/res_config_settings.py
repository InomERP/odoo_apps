# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Instant Sale Sequence Prefix
    instant_sale_sequence_prefix = fields.Char(
        string='Instant Sale Sequence Prefix',
        default='IN/SO',
        config_parameter='mst_instant_sale.sequence_prefix',
    )

    # Auto Validate Delivery
    auto_validate_delivery = fields.Boolean(
        string='Auto Validate Delivery',
        default=True,
        config_parameter='mst_instant_sale.auto_validate_delivery',
    )

    # Auto Create Invoice
    auto_create_invoice = fields.Boolean(
        string='Auto Create Invoice',
        default=True,
        config_parameter='mst_instant_sale.auto_create_invoice',
    )

    # Auto Post Invoice
    auto_post_invoice = fields.Boolean(
        string='Auto Post Invoice',
        default=True,
        config_parameter='mst_instant_sale.auto_post_invoice',
    )

    # Auto Register Payment
    auto_register_payment = fields.Boolean(
        string='Auto Register Payment',
        default=False,
        config_parameter='mst_instant_sale.auto_register_payment',
    )

    # Auto Return Delivery On Cancel
    auto_return_delivery_on_cancel = fields.Boolean(
        string='Auto Return Delivery On Cancel',
        default=True,
        config_parameter='mst_instant_sale.auto_return_delivery_on_cancel',
    )

    # Auto Cancel Invoice On Cancel
    auto_cancel_invoice_on_cancel = fields.Boolean(
        string='Auto Cancel Invoice On Cancel',
        default=True,
        config_parameter='mst_instant_sale.auto_cancel_invoice_on_cancel',
    )

    # Allow Negative Stock
    allow_negative_stock = fields.Boolean(
        string='Allow Negative Stock',
        default=False,
        config_parameter='mst_instant_sale.allow_negative_stock',
    )

    # Allow Partial Delivery
    allow_partial_delivery = fields.Boolean(
        string='Allow Partial Delivery',
        default=True,
        config_parameter='mst_instant_sale.allow_partial_delivery',
    )