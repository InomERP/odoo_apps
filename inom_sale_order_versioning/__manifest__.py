# -*- coding: utf-8 -*-
{
    'name': 'Inom Sale Order Versioning',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Create and manage multiple versions of quotations and sale orders '
               'with a clear version history.',
    'description': """
Sale Order Versioning
=====================
Create multiple versions of a quotation or sale order directly from the order
form. Each new version is a fresh draft copy of the source order that keeps a
clear link back to the original, so the full history of changes stays available.
""",
    'author': 'InomERP',
    'maintainer': 'InomERP',
    'company': 'InomERP',
    'website': 'https://www.inomerp.in',
    'license': 'LGPL-3',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/version_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
