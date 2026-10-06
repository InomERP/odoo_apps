# -*- coding: utf-8 -*-
{
    'name': 'INOM POS Access Management',
    'version': '20.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Manage POS access rights – hide or disable POS buttons per user/employee with a single click.',
    'description': """
Simplify POS Access Management
==============================
Create access rules for multiple users and employees on the Point of Sale (POS) system.
With a single click, specific POS buttons can be hidden or disabled — no technical skills required.

Key Highlights
--------------
* Multiple access rules for multiple users/employees
* Hide / disable buttons per user role
* Organized into 7 access categories:
    - Salesperson Restrictions
    - Payment
    - Order
    - Customer
    - Numpad
    - Action
    - General
* Works on Odoo Online, Odoo.sh, and On-Premise.
""",
    'author': 'InomERP',
    'website': 'https://inomerp.in/',
    'support': 'info@inomerp.in',
    'license': 'LGPL-3',
    'live_test_url': 'https://youtu.be/5diiQ2FOs4c',
    'depends': [
        'point_of_sale',
        'hr',
        'pos_hr',
        'mail',
        'stock',
        'account',
        'sale',
    ],
    'data': [
        'security/pos_access_security.xml',
        'security/ir.access.csv',
        'views/res_users_views.xml',
        'views/pos_access_rights_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'inom_pos_access_management/static/src/overrides/models/pos_store.js',
            'inom_pos_access_management/static/src/overrides/plugins/access_right_plugin.js',
            'inom_pos_access_management/static/src/overrides/components/category_selector.js',
            'inom_pos_access_management/static/src/overrides/components/control_buttons.js',
            'inom_pos_access_management/static/src/overrides/components/payment_screen.js',
            'inom_pos_access_management/static/src/overrides/components/product_screen.js',
            'inom_pos_access_management/static/src/overrides/components/ticket_screen.js',
            'inom_pos_access_management/static/src/overrides/components/templates.xml',
            'inom_pos_access_management/static/src/overrides/styles/pos_access_rights.css',
        ],
        'web.assets_tests': [
            'inom_pos_access_management/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}

