{
    'name': 'Inom Global Auto Mail Sender',
    'version': '1.0.0',
    'summary': 'Automated email notifications for Sales, Purchases, and Invoices',
    'description': """
Global Auto Mail Sender allows you to automatically send emails for
Sales Orders, Purchase Orders, and Invoices based on configurable day intervals.

Key Features:
- Centralized global configuration
- Automatic email sending using scheduled actions
- Supports Sales Orders, Purchase Orders, and Invoices
- Fully configurable email templates
- Prevents duplicate email sending
""",
    'category': 'Tools',
    'author': 'InoMERP',
    'website': 'https://www.inomerp.in',
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'depends': [
        'mail',
        'sale_management',
        'purchase',
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mail_config_views.xml',
        'data/mail_template.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': True,
}
