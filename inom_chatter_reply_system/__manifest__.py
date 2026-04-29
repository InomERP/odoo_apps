{
    "name": "Inom Chatter reply system",
    "version": "18.0.0.0.0",
    "summary": "Enable administrators to impersonate users to manage and respond within chatter conversations.",
    "category": "User Reply",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": ["mail", "base"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "inom_chatter_reply_system/static/src/components/reply_button/reply_button.js"
        ],
    },
    'images': ['static/description/banner.png'],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": 'LGPL-3',
}

