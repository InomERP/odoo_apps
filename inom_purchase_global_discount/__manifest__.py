{
    'name': 'INOM Purchase Global Discount',

    'version': '17.0.1.0.0',

    'summary': 'Global Discount for Purchase Orders (Like Sale & Invoice)',

    'description': """
INOM Purchase Global Discount
=============================

This module allows applying global discount on Purchase Orders
similar to Sales and Invoice discount functionality.

Main Features:
--------------
- Apply global discount on Purchase Orders
- Percentage discount support
- Fixed amount discount support
- Automatic total calculation
- Discount configuration from settings
- Secure access control

Compatible with Odoo 17 Community & Enterprise.
""",

    'author': 'INOM ERP',

    'website': 'https://inomerp.in/',

    'category': 'Purchases',

    'depends': [
        'purchase',
    ],

    'data': [
        'security/ir.model.access.csv',

        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
    ],

    'images': [
        'static/description/banner.png',
    ],

    'installable': True,

    'application': False,

    'license': 'LGPL-3',
}



# {
#     'name': 'INOM Purchase Global Discount',
#     'version': '1.0',
#     'summary': 'Global Discount for Purchase Orders (Like Sale & Invoice)',
#     'author': 'INOM ERP',
#     'category': 'Purchases',
#     'depends': ['purchase'],
#     'data': [
#         'security/ir.model.access.csv',
#         'views/purchase_order_views.xml',
#         'views/res_config_settings_views.xml',
#     ],
#     'installable': True,
# }