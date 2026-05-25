# -*- coding: utf-8 -*-
{
    'name': 'Inom POS Stock Badge',
    'version': '17.0.1.0.0',
    'summary': 'Display real-time stock badge on POS product cards',
    'author': 'InomERP',
    'website': 'https://inomerp.in',
    'category': 'Point of Sale',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'stock',
    ],
    'data': [
        'views/pos_config_settings_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'inom_pos_stock_badge/static/src/css/pos_stock_badge.scss',
            'inom_pos_stock_badge/static/src/xml/pos_stock_badge.xml',
            'inom_pos_stock_badge/static/src/xml/order_summary.xml',
            'inom_pos_stock_badge/static/src/xml/low_stock_button.xml',
            'inom_pos_stock_badge/static/src/js/pos_stock_badge.js',
            'inom_pos_stock_badge/static/src/js/stock_sync.js',
            'inom_pos_stock_badge/static/src/js/payment_screen_patch.js',
            'inom_pos_stock_badge/static/src/js/order_summary.js',
            'inom_pos_stock_badge/static/src/js/low_stock_button.js',
            'inom_pos_stock_badge/static/src/js/navbar_patch.js',
            'inom_pos_stock_badge/static/src/js/models.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
