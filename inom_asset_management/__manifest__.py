{
    'name': 'Inom Asset Management',
    'summary': 'Manage assets and compute depreciation easily',
    'description': """
Inom Asset Management Module
============================

This module helps you to:

- Create Asset Categories
- Manage Assets
- Automatically compute Depreciation
- Track asset values over time

Designed for Odoo 20.
    """,

   
    'author': 'InomERP',

    'website': 'https://inomerp.in/',

    'version': '20.0.1.0.1',
    'category': 'Accounting',

    'depends': [
        'base',
        'account',
    ],

    'data': [
        'security/ir.access.csv',
        'views/asset_category_view.xml',
        'views/asset_view.xml',
        'views/asset_depreciation_line_view.xml',
        'views/menu.xml',
    ],

    'demo': [],
    
    'images': [
        'static/description/banner.png',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,

    'license': 'LGPL-3',
}
