{
    'name': 'Simple Activity Auto Creator',
    'version': '19.0.1.0.0',
    'summary': 'Automatically create activities on SO confirmation and Invoice posting',

    'description': """
Automatically creates follow-up activities when:
- Sales Order is confirmed
- Invoice is posted

Works in Community & Enterprise.
""",

    'category': 'Productivity',
    'author': 'INOM ERP',
    'website': 'https://yourcompany.com',

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

    'installable': True,
    'application': False,
}





# {
#     'name': 'Simple Activity Auto Creator',
#     'version': '1.0',
#     'summary': 'Automatically create activities on SO confirmation and Invoice posting',
#     'description': """
# Automatically creates follow-up activities when:
# - Sales Order is confirmed
# - Invoice is posted

# Works in Community & Enterprise.
# """,
#     'category': 'Productivity',
#     'author': ' INOM ERP',
#     'website': 'https://yourcompany.com',
#     'depends': [
#         'mail',
#         'sale_management',
#         'account',
#         'stock',
#     ],
#     'data': [
#         'security/ir.model.access.csv',
#         'views/activity_rule_views.xml',
#     ],
#     'installable': True,
#     'application': False,
# }
