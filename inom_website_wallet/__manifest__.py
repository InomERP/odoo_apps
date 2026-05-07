# -*- coding: utf-8 -*-
{
    'name': "Inom Website Wallet",
    'version': '18.0.1.0.0',
    'summary': "A complete digital wallet system for Odoo Website customers.",
    'description': """
Website Wallet
==============
A complete e-wallet / digital wallet system for the Odoo Website.

Features
--------
* Customers can recharge their wallet from the website using a configurable
  "Wallet Recharge Product".
* Wallet balance and transaction history available on Customer Portal.
* Customers can use their wallet balance to pay orders on the shop.
* Admin can add money to a customer's wallet manually from the backend.
* Wallet balance is displayed on the partner form view.
* Outstanding wallet credits can be applied to customer invoices.
* Automatic email notification on every wallet recharge.
* Full accounting integration via internal-transfer payments.
""",
    'author': "InomERP",
    'website': "https://inomerp.in",
    'category': 'Website',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'payment',
        'sale_management',
        'website',
        'website_sale',
        'portal',
    ],
    'data': [
        # security
        'security/website_wallet_security.xml',
        'security/ir.model.access.csv',
        # data
        'data/wallet_sequence.xml',
        'data/mail_template_data.xml',
        # wizard
        'wizard/add_wallet_balance_wizard_views.xml',
        # views
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/website_wallet_transaction_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/website_wallet_templates.xml',
        'views/portal_templates.xml',
        'views/website_wallet_menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'inom_website_wallet/static/src/scss/inom_website_wallet.scss',
            'inom_website_wallet/static/src/js/inom_website_wallet.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
