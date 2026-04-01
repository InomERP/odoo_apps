{
    'name': 'Inom Account Overdue Management',
    'version': '19.0.1.0.0',
    'summary': 'Track overdue customer invoices and payment history with smart alerts',
    'description': """
Professional Odoo module for tracking customer overdue invoices,
payment history, smart button alerts, and customer-level warning banners.
This module helps finance teams manage outstanding dues efficiently.
    """,
    'author': 'InomERP',
    'website': 'https://inomerp.in',
    'maintainer': 'InomERP',
    'support': 'info@inomerp.in',
    'category': 'Accounting',
    'license': 'LGPL-3',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_overdue_view.xml',
        'views/res_partner_view.xml',
        'data/cron.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
}