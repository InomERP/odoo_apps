# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - Certificates",
    "version": "18.0.1.1.0",
    "category": "Education",
    "summary": "Certificate templates, QR-verifiable numbering, ID cards.",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": ["inom_university_core"],
    "data": [
        "security/certificate_security.xml",
        "security/ir.model.access.csv",
        "data/certificate_data.xml",
        "views/certificate_views.xml",
        "report/certificate_reports.xml",
        "views/certificate_portal_templates.xml",
        "views/certificate_menus.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "demo": ["demo/certificate_demo.xml"],
    "application": False,
    "installable": True,
}
