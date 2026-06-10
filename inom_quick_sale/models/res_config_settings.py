# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    quick_sale_sequence_prefix = fields.Char(
        string='Quick Sale Sequence Prefix',
        default='IN/SO',
        config_parameter='inom_quick_sale.sequence_prefix',
    )

    auto_validate_delivery = fields.Boolean(
        string='Auto Validate Delivery',
        default=True,
        config_parameter='inom_quick_sale.auto_validate_delivery',
    )

    auto_create_invoice = fields.Boolean(
        string='Auto Create Invoice',
        default=True,
        config_parameter='inom_quick_sale.auto_create_invoice',
    )

    auto_post_invoice = fields.Boolean(
        string='Auto Post Invoice',
        default=True,
        config_parameter='inom_quick_sale.auto_post_invoice',
    )

    auto_register_payment = fields.Boolean(
        string='Auto Register Payment',
        default=False,
        config_parameter='inom_quick_sale.auto_register_payment',
    )

    auto_return_delivery_on_cancel = fields.Boolean(
        string='Auto Return Delivery On Cancel',
        default=True,
        config_parameter='inom_quick_sale.auto_return_delivery_on_cancel',
    )

    auto_cancel_invoice_on_cancel = fields.Boolean(
        string='Auto Cancel Invoice On Cancel',
        default=True,
        config_parameter='inom_quick_sale.auto_cancel_invoice_on_cancel',
    )

    allow_negative_stock = fields.Boolean(
        string='Allow Negative Stock',
        default=False,
        config_parameter='inom_quick_sale.allow_negative_stock',
    )

    allow_partial_delivery = fields.Boolean(
        string='Allow Partial Delivery',
        default=True,
        config_parameter='inom_quick_sale.allow_partial_delivery',
    )
