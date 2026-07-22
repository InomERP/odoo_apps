# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - Hostel",
    "version": "18.0.1.0.0",
    "category": "Education",
    "summary": "Hostel structure, allotment with deposit + fee bridge, complaints.",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": ["inom_university_core", "inom_university_fee"],
    "data": [
        "security/hostel_security.xml",
        "security/ir.model.access.csv",
        "data/hostel_data.xml",
        "views/hostel_views.xml",
        "report/hostel_reports.xml",
        "views/hostel_portal_templates.xml",
        "views/hostel_menus.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "demo": ["demo/hostel_demo.xml"],
    "application": False,
    "installable": True,
}
