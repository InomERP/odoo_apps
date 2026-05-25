# -*- coding: utf-8 -*-
{
    'name': 'Inom POS Stock Badge',
    'version': '18.0.1.0.0',
    'summary': 'Display real-time stock badge on POS product cards',
    'description': """
        Feature 1: Stock Badge on POS Product Card
        ==========================================
        - Displays real-time stock quantity as a colored badge on every product card
        - Red badge for out-of-stock, Orange for low stock, Green (custom) for normal
        - Configurable badge position: Top Left, Top Right, Bottom Right
        - Configurable badge colors via hex color picker
        - Low stock threshold setting
        - Master toggle to enable/disable the entire feature
    """,
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
        'point_of_sale.base_app': [
            'inom_pos_stock_badge/static/src/css/pos_stock_badge.scss',
            'inom_pos_stock_badge/static/src/xml/pos_stock_badge.xml',
            'inom_pos_stock_badge/static/src/xml/order_summary.xml',
            'inom_pos_stock_badge/static/src/js/pos_stock_badge.js',
            'inom_pos_stock_badge/static/src/js/stock_sync.js',
            'inom_pos_stock_badge/static/src/js/payment_screen_patch.js',
            'inom_pos_stock_badge/static/src/js/order_summary.js',
            'inom_pos_stock_badge/static/src/js/low_stock_button.js',
            'inom_pos_stock_badge/static/src/js/navbar_patch.js',
            'inom_pos_stock_badge/static/src/xml/low_stock_button.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
