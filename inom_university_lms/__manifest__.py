# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - LMS",
    "version": "17.0.1.0.0",
    "category": "Education",
    "summary": "Study materials, assignments, online submission and grading.",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": ["inom_university_academics"],
    "data": [
        "security/lms_security.xml",
        "security/ir.model.access.csv",
        "views/lms_views.xml",
        "report/lms_reports.xml",
        "views/lms_portal_templates.xml",
        "views/lms_menus.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "demo": ["demo/lms_demo.xml"],
    "application": False,
    "installable": True,
}
