{
    'name': 'Inom Automatic Activity Auto Creator',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Automatically create activities on Sales Order confirmation and Invoice posting',

    'description': """
This module automatically creates follow-up activities in Odoo based on key business actions,
helping teams stay organized and never miss important tasks.

Key Features:
• Auto-create activities on Sales Order confirmation  
• Auto-create activities on Invoice posting  
• Configurable activity rules (user, due date, notes)  
• Reduces manual work and improves productivity  
• Seamless integration with Sales and Accounting  
• Compatible with Odoo 18  

Ideal for businesses that want to automate workflow activities and ensure timely follow-ups.
""",

    'website': 'https://inomerp.in/',
    'author': 'InomERP',

    'depends': [
        'mail',
        'sale_management',
        'account',
        'stock',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/activity_rule_views.xml',
    ],

    'images': ['static/description/banner.png'],

    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}







