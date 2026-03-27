{
    'name': 'Sale Global Discount Approval',

    'version': '19.0.1.0.0',

    'summary': 'Global Discount with Approval Workflow on Sale Order and Invoice',

    'description': """
Sale Global Discount Approval
=============================

This module allows applying a global discount on Sales Orders and Invoices
with an approval workflow.

Main Features:
--------------
- Apply global percentage discount
- Apply fixed amount discount
- Approval workflow for discount validation
- Automatic discount reflection on invoice
- Configurable approval settings
- Secure access control

Compatible with Odoo 19 Community & Enterprise.
""",

    'category': 'Sales',

    'website': 'https://inomerp.in/',
    'author': 'InomERP',

    'depends': [
        'sale_management',
        'account',
        'mail',
    ],

    'data': [
        'security/ir.model.access.csv',

        'views/sale_order_views.xml',
        'views/account_move_view.xml',
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
#     'name': 'Sale Global Discount Approval',
#     'version': '1.0',
#     'summary': 'Global Discount with Approval Workflow',
#     'description': 'Apply global discount on sale order and invoice with approval workflow.',
#     'author': 'Custom',
#     'depends': [
#         'sale_management',
#         'account'
#     ],
#     'data': [
#         'security/ir.model.access.csv',
#         'views/sale_order_views.xml',
#         'views/res_config_settings_views.xml',
#         'views/account_move_view.xml',
#     ],
#     'installable': True,
#     'application': False,
# }
