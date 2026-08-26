# -*- coding: utf-8 -*-
{
    "name": "Inom User Wise Hidden Menu",
    "version": "18.0.1.0.0",
    "summary": "Hide specific menus for selected users",
    "description": """
User Wise Hidden Menu
=====================

This module allows administrators to hide specific menu items for selected users.
It provides a a configuration option in the user form to select menus that should
be hidden for that particular user.

Features:
---------
- Hide specific menus for individual users
- Easy configuration from the User form
- Better UI control for administrators
""",
    "author": "InomERP",
    "website": "https://inomerp.in/",
    "support": "info@inomerp.in",
    'images': ['static/description/banner.png'],
    "category": "Tools",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "views/res_users_view.xml",
    ],
    "installable": True,
    "application": True,
}

