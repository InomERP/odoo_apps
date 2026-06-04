# -*- coding: utf-8 -*-
{
    'name': 'Odoo Sales Automation | Auto Invoice | Auto Delivery',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Instant Sales Automation - Auto Invoice, Auto Delivery, Auto Cancel',
    'author': 'Mind Spark Technologies LLP',
    'website': 'https://mindsparktechnologies.com',
    'depends': [
        'sale_management',
        'stock',
        'account',
        'sale_stock',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}