# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wallet_enabled = fields.Boolean(
        string='Use Wallet',
        config_parameter='inom_website_wallet.wallet_enabled',
        help='Enable the digital wallet system on the website.',
    )
    wallet_recharge_product_id = fields.Many2one(
        'product.product',
        string='Wallet Recharge Product',
        config_parameter='inom_website_wallet.wallet_recharge_product_id',
        help='Product used as the wallet recharge service. The unit price '
             'entered by the customer on the wallet page is set as the '
             'price of this product line in the cart.',
        domain=[('type', '=', 'service'), ('sale_ok', '=', True)],
    )
    wallet_min_recharge = fields.Float(
        string='Minimum Recharge Amount',
        config_parameter='inom_website_wallet.wallet_min_recharge',
        default=1.0,
    )
    wallet_max_recharge = fields.Float(
        string='Maximum Recharge Amount',
        config_parameter='inom_website_wallet.wallet_max_recharge',
        default=10000.0,
    )

    @api.model
    def get_wallet_recharge_product(self):
        """Return the configured Wallet Recharge product (or False)."""
        param = self.env['ir.config_parameter'].sudo().get_param(
            'inom_website_wallet.wallet_recharge_product_id'
        )
        if not param:
            return self.env['product.product']
        try:
            return self.env['product.product'].browse(int(param)).exists()
        except (TypeError, ValueError):
            return self.env['product.product']

    @api.model
    def is_wallet_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'inom_website_wallet.wallet_enabled'
        ) in ('True', 'true', '1', True)
