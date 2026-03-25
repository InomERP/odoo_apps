{
    'name': 'Inom Simple Activity Auto Creator',
    'version': '17.0.1.0.0',
    'summary': 'Automatically create activities on Sales Order confirmation and Invoice posting',

    'description': """
Automatically creates follow-up activities when:
- Sales Order is confirmed
- Invoice is posted

Works in Community.
""",

    'category': 'Productivity',
    'author': 'INOM ERP',
    'website': 'https://inomerp.in',

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

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}



