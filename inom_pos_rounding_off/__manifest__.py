{
    'name': 'INOM POS Rounding Off Amount',
    'version': '18.0.1.1.0', 
    'category': 'Point of Sale',
    'summary': 'Advanced POS rounding with manual & automatic modes, precision control, and accounting integration',

    'description': """
POS Rounding Off Module

This module provides advanced rounding functionality in Point of Sale.

Key Features:
----------------------
- Manual Rounding
- Automatic Rounding
- Configurable Rounding Precision
- Rounding based on Payment Method
- Receipt Rounding Display
- Backend Rounding Storage
- Settings Configuration Panel
- Update Rounding Dynamically
- POS Visibility Toggle
- Automatic Journal Entries for Rounding

Use Case:
----------------------
Ideal for businesses handling cash transactions where rounding off is required 
(e.g., nearest 0.05, 0.10, or 1.00).

Fully integrated with Odoo POS and Accounting.
""",

    'author': 'Inom',
    'website': 'https://inomerp.in/',
    'license': 'LGPL-3',

    'depends': [
        'point_of_sale',
        'account',
    ],

    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data
        'data/pos_rounding_data.xml',

        # Views
        'views/pos_config_views.xml',
        'views/pos_payment_method_views.xml',
        'views/pos_order_views.xml',
    ],

    'assets': {
        'point_of_sale._assets_pos': [
            'inom_pos_rounding_off/static/src/js/pos_rounding.js',
            'inom_pos_rounding_off/static/src/xml/pos_rounding_templates.xml',
        ],
    },

    'images': [
        'static/description/banner.png', 
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}















# {
#     'name': 'POS Rounding Off Amount',
#     'version': '19.0.1.0.0',
#     'category': 'Point of Sale',
#     'summary': 'Round off the amount in POS while payment is made',
#     'author': 'InomERP',
#     'website': 'https://www.inom.com',

    
#     'depends': [
#         'point_of_sale',  
#         'account',        
#     ],

    
#     'data': [
#         'security/ir.model.access.csv',  
#         'data/pos_rounding_data.xml',     
#         'views/pos_config_views.xml',     
#         'views/pos_payment_method_views.xml',
#         'views/pos_order_views.xml',
#     ],

    
#     'assets': {
#         'point_of_sale._assets_pos': [
#             'inom_pos_rounding_off/static/src/js/pos_rounding.js',       
#             'inom_pos_rounding_off/static/src/xml/pos_rounding_templates.xml', 
#         ],
#     },

#     'license': 'LGPL-3',
#     'installable': True,
#     'auto_install': False,
#     'application': False,
# }
