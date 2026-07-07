# -*- coding: utf-8 -*-
{
    "name": "Inom Advanced Sales Dashboard",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Real-time Sales Analytics Dashboard and Reporting Suite for Odoo 18 Community",
    "description": """
Advanced Sales Dashboard
========================
Phase 1 - Foundation & Setup.

This phase delivers the module skeleton only: folder structure, manifest,
security, menus, the dashboard client action shell (empty branded page),
the sales revenue target model skeleton with basic list/form views, and
the Chart.js asset registration. No KPIs, aggregation, charts, filters or
reports are implemented in this phase.
    """,
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "account",
        "stock",
        "sale_stock",
        "contacts",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sales_target_views.xml",
        "views/dashboard_menus.xml",
        "views/report_views.xml",
        "views/sales_detail_report_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "inom_advance_sales_dashboard/static/lib/chartjs/chart.umd.js",
            "inom_advance_sales_dashboard/static/lib/html2canvas/html2canvas.min.js",
            "inom_advance_sales_dashboard/static/src/scss/dashboard.scss",
            "inom_advance_sales_dashboard/static/src/scss/widget_menu.scss",
            "inom_advance_sales_dashboard/static/src/scss/dashboard_theme.scss",
            "inom_advance_sales_dashboard/static/src/js/widget_style_store.js",
            "inom_advance_sales_dashboard/static/src/js/fontawesome_icons.js",
            "inom_advance_sales_dashboard/static/src/js/widget_menu.js",
            "inom_advance_sales_dashboard/static/src/js/dashboard.js",
            "inom_advance_sales_dashboard/static/src/xml/widget_menu.xml",
            "inom_advance_sales_dashboard/static/src/xml/dashboard.xml",
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    "installable": True,
    "application": True,
}
