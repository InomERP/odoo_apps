{
    "name": "Odoo Readonly User",
    "version": "18.0.0.0.0",
    "summary": "Enable Readonly User",
    "category": "Access Control",
    "author": "InomERP",
    "support": "info@inomerp.in",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/readonly_user.xml",
    ],
    'images': ['static/description/banner.png'],
    "application": True,
    "installable": True,
    "auto_install": False,
}
