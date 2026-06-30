{
    'name': 'Inom Contract Management',
    'version': '19.0.3.0.0',
    'category': 'Sales/Contract',
    'summary': 'Dynamic contract management with customizable approval workflows',
    'description': """
Contract Management
====================
This module improves contract management and the approval process. It
provides a dynamic, customizable and flexible approval system for
contracts. Approved/validated contracts can be used to create customer
invoices and vendor bills.

Key Features
------------
* Contract validation with or without an approval process
* Organize approval workflow using Teams
* Unlimited steps/levels of contract approval with email notifications
* Quickly create new contracts from contract templates
* Use contracts as templates for customer invoices / vendor bills
* Auto expire/close contracts based on End Date or Last Payment Date
* Multi-Company and Multi-Currency support
* Any user can initiate (add) a contract
    """,
    'author': 'InomERP',
    'support': 'info@inomerp.in',
    'website': 'https://inomerp.in',
    'license': 'LGPL-3',
    'depends': ['mail', 'product', 'account'],
    'data': [
        'security/contract_security.xml',
        'security/ir.model.access.csv',
        'data/contract_sequence.xml',
        'data/mail_template_data.xml',
        'data/contract_cron.xml',
        'views/res_config_settings_views.xml',
        'reports/contract_report.xml',
        
        'views/inom_contract_views.xml',
        'views/account_move_views.xml',
        'wizards/inom_contract_return_wizard_views.xml',
        'views/contract_dashboard_views.xml',
        'views/contract_menus.xml',
    ],
    
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
