# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - Library",
    "version": "18.0.1.0.0",
    "category": "Education",
    "summary": "Library catalogue, circulation, fines posted to the fee ledger.",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": ["inom_university_core", "inom_university_fee"],
    "data": [
        "security/library_security.xml",
        "security/ir.model.access.csv",
        "data/library_data.xml",
        "views/library_views.xml",
        "report/library_reports.xml",
        "views/library_portal_templates.xml",
        "views/library_menus.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "demo": ["demo/library_demo.xml"],
    "application": False,
    "installable": True,
}
