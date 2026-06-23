# -*- coding: utf-8 -*-
{
    'name': ' INOM Multi-User Inventory Count',
    'version': '18.0.7.2.0',
    'category': 'Inventory/Inventory',
    'summary': 'Session-based multi-user physical inventory / stock take management',
    'description': """
Multi-User Inventory Count
==========================

Enterprise-grade physical inventory / stock take solution for Odoo 19.

Phase 1 - Core Inventory Count Setup
------------------------------------
* Inventory Count document (header) with Approver, Warehouse, Location and Count Type.
* Count types: Single Session / Multi Session.
* Products tab to list the items to be counted (Internal Reference, Name, Barcode).
* Status workflow: Draft -> In Progress -> To Be Approved -> Validated / Rejected.
* Dedicated menu structure with auto-numbered count references (INV/C/XXXXXXX).

Phase 2 - Session Management (Single Session)
---------------------------------------------
* Create Session wizard to assign user(s) and auto-generate counting session(s).
* Session document (INV/S/XXXXXXX) with counting lines (product x location).
* Session timer: Start / Pause / Submit with consumed-time tracking.
* Scan / Unscan per line and optional barcode-driven counting.
* User calculation-mistake flag on session lines.

Phase 3 - Multi-User & Multi-Session
------------------------------------
* Multiple sessions under one inventory count (multi-session) with a session smart button.
* Sessions kanban grouped by status (Draft / In Progress / Submitted).
* Complete Counting aggregates submitted sessions into result lines.
* Inventory Count Lines with theoretical (stock.quant), counted and discrepancy quantities.

Phase 4 - Approve / Reject & Re-Session
--------------------------------------
* Line-level and bulk approve / reject of session lines (rejected lines highlighted).
* Create a re-session from rejected lines, linked back to the parent session.
* Count-level Validate applies counted quantities as inventory adjustments (stock moves).
* Count-level Reject sends the count back for recounting.

Phase 5 - Reports
-----------------
* Inventory Count Report (theoretical vs counted vs discrepancy) - list / pivot / graph.
* Adjustment Report with overstock / out-of-stock categorization.
* User Statistic Report (lines counted and calculation mistakes per user).

Phase 6 - Dashboard & Planner
-----------------------------
* Informative dashboard with live, color-coded session cards.
* Pending Progress menu listing counts currently in progress.
* Planner with scheduled action (ir.cron) to auto-create counts at a set frequency.
    """,
    'website': 'https://inomerp.in',
    'author': 'InomERP',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'mail',
    ],
    'data': [
        'security/inventory_count_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'wizard/create_session_wizard.xml',
        'wizard/scan_count_wizard.xml',
        'views/inventory_count_views.xml',
        'views/inventory_session_views.xml',
        'report/inventory_count_report.xml',
        'report/adjustment_report.xml',
        'report/user_statistic_report.xml',
        'views/inventory_dashboard_views.xml',
        'views/inventory_planner_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inom_multi_user_inventory_count/static/src/js/barcode_scan_button.js',
            'inom_multi_user_inventory_count/static/src/xml/barcode_scan_button.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
