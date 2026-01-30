{
    'name': 'Inom Invoice Merge',
    'version': '19.0.1.0',
    'category': 'Accounting',
    'summary': 'Merge multiple draft invoices into a single invoice',
    'description': """
Inom Invoice Merge module allows accountants to merge multiple draft invoices
into a single invoice with ease.

Key Features:
• Merge multiple draft customer invoices or vendor bills  
• Ensures same partner, currency, company, and invoice type  
• Option to keep or cancel original invoices after merge  
• Simple and user-friendly merge wizard  
• Fully integrated with Odoo Accounting  
• Compatible with Odoo 19  

This module is ideal for accounting teams who want to reduce invoice clutter,
simplify billing, and improve financial accuracy by consolidating invoices.
""",
    'website': 'https://inomerp.in/',
    'author': 'InomERP',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/invoice_merge_wizard_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
