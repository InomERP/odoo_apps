# -*- coding: utf-8 -*-
{
    "name": "Website Self-Service Attendance",
    "version": "18.0.1.0.0",
    "category": "Human Resources/Attendances",
    "summary": "Employees record and review their own attendance from the "
               "website, with worked and extra hours.",
    "description": """
Website Self-Service Attendance
===============================

Gives portal employees a self-service attendance area on the website.
From the portal an employee can:

* Check in and check out without opening the backend.
* Review their full attendance history with worked hours and extra hours.
* Filter records by a custom date range.
* Sort, group and paginate the attendance list.
* Open a detail page for any single attendance record.

The module only reads and writes the standard ``hr.attendance`` records, so
everything stays in sync with the native Attendances application. No Odoo core
behaviour is replaced; the feature is added through clean portal inheritance.
    """,
    "author": "InomERP",
    "company": "InomERP Pvt Ltd",
    "maintainer": "InomERP",
    "website": "https://inomerp.in",
    "license": "OPL-1",
    "depends": [
        "hr_attendance",
        "portal",
        "website",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/portal_attendance_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "inom_portal_attendance/static/src/scss/portal_attendance.scss",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
