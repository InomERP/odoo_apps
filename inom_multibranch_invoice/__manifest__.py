# -*- coding: utf-8 -*-
{
    "name": "Inom Multi Branch Invoice & Accounting",
    "version": "19.0.1.5.1",
    "category": "Accounting/Accounting",
    "summary": "One Company | Multiple Branches | Complete Accounting Control",
    "description": """
Multi Branch Invoice & Accounting
========================================
Run several operating units (branches) inside one company and keep their
accounting separated. A branch can be set on customer invoices, vendor bills,
credit notes, refunds, journal entries, journal items, payments, bank statement
lines and receipts. Branch level record rules make sure a branch user only sees
its own data while a branch manager sees everything. Includes optional branch
wise document numbering, a branch performance dashboard and full audit tracking.
""",
    "author": "InomERP",
    "company": "InomERP Pvt Ltd",
    "maintainer": "InomERP Pvt Ltd",
    "website": "https://www.inomerp.in",
    "license": "LGPL-3",
    "depends": ["account", "mail"],
    "data": [
        "security/inom_branch_security.xml",
        "security/ir.model.access.csv",
        "data/inom_branch_sequence.xml",
        "views/inom_branch_views.xml",
        "views/res_users_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "report/inom_multibranch_invoice_report.xml",
        "views/inom_branch_dashboard_views.xml",
        "views/inom_branch_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "inom_multibranch_invoice/static/src/branch_switch/*.js",
            "inom_multibranch_invoice/static/src/branch_switch/*.xml",
            "inom_multibranch_invoice/static/src/dashboard/*.js",
            "inom_multibranch_invoice/static/src/dashboard/*.xml",
            "inom_multibranch_invoice/static/src/dashboard/*.scss",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
}
