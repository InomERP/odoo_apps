# -*- coding: utf-8 -*-
{
    "name": "Healthcare POS",
    "version": "17.0.1.0",
    "category": "Healthcare",
    "summary": "Custom standalone Point of Sale for the Inom Healthcare System",
    "description": """
Healthcare POS
==============
A dedicated, custom Point of Sale built specifically for the Inom Healthcare
System. This is NOT Odoo's default point_of_sale module — it is a standalone
OWL-based POS client with an Odoo-POS-like experience tailored to healthcare
operations.

Features
--------
* Custom POS interface (sessions, cart, numpad, payment, receipt) similar to Odoo POS.
* Healthcare operations exposed in POS: consultations, lab, radiology, pharmacy,
  treatments and procedures sold as POS services.
* Patient integration: patients auto-load into the POS, can be searched, selected
  and created in-screen without leaving the POS.
* Session lifecycle with opening/closing cash control.
* Multiple concurrent sessions, multi-company, multi-currency and multi-branch
  (each terminal/branch runs its own configuration and session).
* On payment: optional hospital billing + clinical record generation
  (lab / radiology / treatment) and pharmacy stock decrement.
    """,
    "author": "InomERP",
    "website": "https://www.inomerp.com",
    "license": "LGPL-3",
    "depends": ["inom_healthcare_system"],
    "data": [
        "security/pos_security.xml",
        "security/ir.model.access.csv",
        "data/pos_sequence.xml",
        "data/pos_data.xml",
        "views/pos_config_views.xml",
        "views/pos_session_views.xml",
        "views/pos_order_views.xml",
        "views/pos_service_views.xml",
        "views/pos_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "inom_healthcare_pos/static/src/css/pos_receipts.css",
            "inom_healthcare_pos/static/src/scss/pos.scss",
            "inom_healthcare_pos/static/src/scss/pos_dashboard.scss",
            "inom_healthcare_pos/static/src/app/pos_store.js",
            "inom_healthcare_pos/static/src/app/pos_dashboard.js",
            "inom_healthcare_pos/static/src/app/pos_app.js",
            "inom_healthcare_pos/static/src/app/pos_dashboard.xml",
            "inom_healthcare_pos/static/src/app/pos_templates.xml",
        ],
    },
    'images': ['static/description/banner.png'],
    "application": True,
    "installable": True,
}
