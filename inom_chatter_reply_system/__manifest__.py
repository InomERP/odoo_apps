{
    "name": "Inom Chatter reply system",
    "version": "20.0.1.0.0",
    "summary": "Enable administrators to impersonate users to manage and respond within chatter conversations.",
    "category": "User Reply",
    "author": "InomERP",
    "website": "https://inomerp.in",
    'live_test_url': 'https://www.youtube.com/watch?v=5wUMZ7a-B7s',

    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "inom_chatter_reply_system/static/src/components/reply_button/reply_button.scss",
            "inom_chatter_reply_system/static/src/components/reply_button/reply_button.xml",
            "inom_chatter_reply_system/static/src/components/reply_button/reply_button.js",
        ],
        "web.assets_tests": [
            "inom_chatter_reply_system/static/tests/tours/**/*",
        ],
    },
    'images': ['static/description/banner.png'],
    "application": True,
    "installable": True,
    "auto_install": False,
}
