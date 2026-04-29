{
    'name': 'Inom Asset Management',
    'version': '18.0.1.0.0',
    'summary': 'A smart and efficient solution by InomERP to manage, track, and control your company assets with ease.',
    'description' : 'A smart and efficient solution by InomERP to manage, track, and control your company assets with ease',
    'depends': ['base', 'account'],
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",

    'data': [
        'security/ir.model.access.csv',
        'views/asset_category_view.xml',
        'views/asset_view.xml',
        'views/asset_depreciation_line_view.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
