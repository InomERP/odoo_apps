# -*- coding: utf-8 -*-
{
    'name': ' INOM POS Product by Lot/Serial Number',
    'version': '19.0.1.5.6',
    'category': 'Sales/Point of Sale',
    'summary': 'Scan, select, manage, and print Lot/Serial Numbers directly from the POS',
    'description': """
POS Product by Lot/Serial Number
================================
Enable POS users to:

* Scan products via Lot/Serial Number barcode (Phase 3)
* Select lots from a searchable popup (Phase 2)
* Manual entry + live autocomplete (Phase 2)
* Quantity validation against lot stock (Phase 3)
* Real-time qty reflection across order (Phase 4)
* Duplicate-serial prevention (Phase 4)
* Unknown-lot prompt with in-POS create (Phase 4)
* Offline mode with IndexedDB cache + reconnect sync (Phase 5)
* Receipt + backend views show lot/serial numbers (Phase 6)

Compatible with Odoo 19 Community & Enterprise.
""",
    'author': 'Inom',
    'website': 'https://inomerp.in/',
    'support': 'info@inomerp.in',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'stock',
        'product',
    ],
    'data': [
        # security MUST load before any data referencing groups
        'security/pos_lot_security.xml',
        'security/ir.model.access.csv',
        # seed / default data
        'data/pos_config_data.xml',
        # views
        'views/pos_config_views.xml',
        'views/stock_lot_views.xml',
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'inom_pos_product_by_lot_number/static/src/scss/**/*.scss',
            'inom_pos_product_by_lot_number/static/src/js/**/*.js',
            'inom_pos_product_by_lot_number/static/src/xml/**/*.xml',
        ],
    },
    # Post-init: grant lot-create rights to existing POS Managers
    # (done in Python to avoid Odoo 19's cross-module XML update fragility).
    'images': ['static/description/banner.png'],
    'post_init_hook': '_post_init_set_groups',
    'installable': True,
    'application': False,
    'auto_install': False,
}
