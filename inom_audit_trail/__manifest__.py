# -*- coding: utf-8 -*-
{
    "name": "Audit Trail - Track Changes, User Activity Log & Field History",
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "summary": "Audit Trail for Odoo: log who changed what & when. Track "
               "create/read/write/delete per model, field-level old->new value "
               "history, user IP address, browser & login activity, with a live "
               "audit dashboard. GDPR, SOX, HIPAA & ISO 27001 ready.",
    "description": """Audit Trail for Odoo - track who changed what, when and from where.

The complete audit log / activity tracking solution for Odoo. Create rule-based
logging on ANY object (model) and record Create, Read, Update and Delete
operations. For updates, capture full field-level history with the exact old
value and new value, the user who made the change, their IP address and browser,
and an optional GeoIP location. A live dashboard shows active users right now,
today's activity versus yesterday, and your active rules.

Key features:
* Rule-based tracking per Odoo object / model (res.partner, sale.order, account.move, and any custom model)
* Log Create / Read / Update / Delete operations
* Field-level change history: old value to new value for the fields you choose
* Restrict logging to specific user groups
* Capture user IP address, browser / OS, and (optional) GeoIP location
* Live audit dashboard: active users now, activity today vs yesterday, active rules
* Searchable, filterable, groupable audit log
* Works with custom modules out of the box - no per-model coding required

Great for compliance, data security and accountability: GDPR, SOX, HIPAA, ISO 27001.

Compatible with Odoo 17, 18 and 19 - Community and Enterprise.

Brought to you by InomERP - https://inomerp.in - support: info@inomerp.in
""",
    "author": "InomERP",
    "maintainer": "InomERP",
    "company": "InomERP",
    "website": "https://inomerp.in",
    "support": "info@inomerp.in",
    "license": "LGPL-3",
    "depends": ["base", "web", "bus"],
    "data": [
        "security/inom_audit_trail_security.xml",
        "security/ir.model.access.csv",
        "views/inom_audit_trail_rule_views.xml",
        "views/inom_audit_trail_log_views.xml",
        "views/audit_dashboard_views.xml",
        "views/inom_audit_trail_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "inom_audit_trail/static/src/dashboard/audit_dashboard.scss",
            "inom_audit_trail/static/src/dashboard/audit_dashboard.js",
            "inom_audit_trail/static/src/dashboard/audit_dashboard.xml",
        ],
    },
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_dashboard.png",
    ],
    "application": True,
    "installable": True,
}
