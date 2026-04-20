{
    'name': 'inom_pg_query_toolkit',
    'version': '18.0.0.0',
    'category': 'Tools',
    'summary': 'An advanced Odoo module for executing PostgreSQL queries and managing database operations efficiently.',
    'description': """
    PostgreSQL Query Talk is a powerful Odoo module that allows users to execute and manage PostgreSQL queries directly from the Odoo interface.
    This module provides an easy and efficient way to interact with the database, making it useful for developers, administrators, and advanced users who need direct access to database operations.
    This module enhances productivity by simplifying database interactions without leaving the Odoo environment.
    """,
    "images": [
        "static/description/banner.png", ],
    "license": "LGPL-3",
    "author": "InomERP",
    "website": "https://inomerp.in/",

    'depends': ['base','web','mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/querytool.xml',
        'wizard/pdforientation.xml',
         'report/print_pdf.xml',
         'data/data.xml'
      ],
    'images': [
        'static/description/banner.png',
    ],

    'installable': True,
    'application': True,
    "auto_install": False,

}