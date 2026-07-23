# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - Transport",
    "version": "18.0.1.0.0",
    "category": "Education",
    "summary": "Routes, stops, vehicles, drivers and route-wise transport fees.",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": ["inom_university_core", "inom_university_fee"],
    "data": [
        "security/transport_security.xml",
        "security/ir.model.access.csv",
        "data/transport_data.xml",
        "views/transport_views.xml",
        "report/transport_reports.xml",
        "views/transport_portal_templates.xml",
        "views/transport_menus.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "demo": ["demo/transport_demo.xml"],
    "application": False,
    "installable": True,
}
