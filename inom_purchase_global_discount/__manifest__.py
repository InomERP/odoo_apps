{
    'name': 'INOM Purchase Global Discount',

    'version': '1.0',

    'summary': 'Global Discount for Purchase Orders',

    'description': """
INOM Purchase Global Discount
=============================

This module allows applying a global discount on Purchase Orders.

Main Features:
--------------
- Apply global discount on purchase orders
- Percentage discount support
- Fixed amount discount support
- Automatic total calculation
- Configurable discount settings
- Secure access control

Compatible with Odoo Community & Enterprise.
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
#     'summary': 'Global Discount for Purchase Orders',
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