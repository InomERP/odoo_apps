# -*- coding: utf-8 -*-
{
    "name": "Smart Chatter View",
    "version": "1.0.0",
    "summary": "Enhances the chatter interface with improved usability and better message tracking.",
    "description": """The Advanced Chatter View module extends the standard Odoo chatter functionality by introducing UI enhancements and 
    improved interaction features. It enables better message visibility, organized communication threads, and a smoother user experience, making collaboration more efficient across different business processes.
""",

    "category": "",
    "license": "LGPL-3",
    "author": "InomERP",
    "website": "https://inomerp.in/",

    "depends": [
        "base",
        "mail",
        "web",
    ],

    "data": [
        
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
