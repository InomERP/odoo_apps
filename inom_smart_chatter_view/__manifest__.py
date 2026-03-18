# -*- coding: utf-8 -*-
{
    "name": "Inom Smart Chatter View",
    "version": "1.0.0",
    "summary": "Modern Chatter Enhancements with Floating Actions and Side Panel",
    "description": """
Advanced Chatter View Module for Odoo
-------------------------------------

This module enhances the default Odoo chatter interface by introducing a
modern and improved user experience.

Key Features:
-------------
- Floating action icons for better accessibility
- Improved side panel layout
- Clean and responsive UI design
- Enhanced chatter interaction experience
- Seamless integration with Odoo Mail module

Technical Highlights:
---------------------
- Built using Odoo OWL framework
- Fully compatible with web backend assets
- Clean asset structure for scalability
- Easy to customize and extend

Ideal For:
----------
- Companies looking to modernize Odoo UI
- Projects requiring improved chatter usability
- Developers building advanced mail customizations
""",

    "category": "Productivity",
    "license": "LGPL-3",
    "author": "InomERP",
    "website": "https://inomerp.in/",

    "depends": [
        "base",
        "mail",
        "web",
    ],

    "data": [
        # Add XML views here if required
    ],

    "assets": {
        "web.assets_backend": [
            "inom_smart_chatter_view/static/src/js/**/*.js",
            "inom_smart_chatter_view/static/src/css/**/*.css",
            "inom_smart_chatter_view/static/src/xml/**/*.xml",
        ],
    },

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}
