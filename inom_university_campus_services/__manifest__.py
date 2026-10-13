# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - Campus Services",
    "version": "20.0.1.0.0",
    "category": "Education",
    "summary": "Unified student self-service portal and faculty workspace across "
               "all campus services.",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": [
        # "inom_university_core",
        # "inom_university_admission",
        # "inom_university_fee",
        # "inom_university_academics",
        # "inom_university_library",
        # "inom_university_hostel",
        # "inom_university_transport",
        # "inom_university_lms",
        # "inom_university_certificate",
    ],
    "data": [
        "views/campus_portal_templates.xml",
        "views/campus_views.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "application": True,
    "installable": True,
    'price': 50.00,
    'currency': 'USD',
}
