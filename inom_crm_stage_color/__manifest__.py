{
    'name': 'Inom CRM Stage Color',
    'version': '18.0.1.0.0',
    'summary': 'Add custom colors to CRM stages for better pipeline visualization',
    'description': """
Inom CRM Stage Color
====================

Inom CRM Stage Color enhances the default Odoo CRM pipeline by allowing
users to assign custom colors to CRM stages. This improves visual clarity
and makes it easier for sales teams to track opportunities in the pipeline.

Key Features
------------
* Assign custom colors to CRM stages
* Improve pipeline visibility and organization
* Easily identify opportunity progress
* Clean and user-friendly interface
* Fully integrated with the standard Odoo CRM pipeline

Benefits
--------
* Better sales pipeline tracking
* Faster opportunity recognition
* Improved user experience
* More visually organized CRM interface
""",

    'author': 'InomERP',
    'website': 'https://inomerp.in',
    'category': 'Sales/CRM',
    'license': 'LGPL-3',

    'depends': ['crm'],

    'data': [
        'views/crm_stage_views.xml',
        'views/crm_lead_kanban_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'inom_crm_stage_color/static/src/css/kanban_stage_color.css',
        ],
    },

    'images': [
        'static/description/banner.png'
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}