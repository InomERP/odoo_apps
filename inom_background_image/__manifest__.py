{
    'name': 'Inom Dynamic Login Background Manager',

    'version': '1.0.0',

    'summary': 'Set a custom login background image from company settings in Odoo',

    'description': """
Inom Dynamic Login Background Manager allows administrators to set a custom
background image for the Odoo login page directly from the company settings.

After installing the module, a Login Background field will appear in the
company form where users can upload an image. Once saved, the image will
automatically appear on the Odoo login screen.

The module works without modifying core Odoo files and provides a simple
way to personalize the login page for branding and better user experience.
""",

    'author': 'InomERP',

    'website': 'https://www.inomerp.in',

    'category': 'Tools',

    'depends': ['base', 'web'],

    'data': [
        'views/company_view.xml',
        'views/login_template.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}