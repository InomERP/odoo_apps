# -*- coding: utf-8 -*-
{
    "name": " INOM Product Multi Unit of Measure",
    "version": "17.0.4.4.2",
    "category": "Sales/Inventory",
    "summary": "Sell and manage a single product in multiple Units of Measure.",
    "description": """
Product Multi Unit of Measure
=============================
A 1:1 Odoo 17 replica of the Cybrosys "Product Multi UoM" app.

Phase 1 - Module Scaffold & Configuration (F-01).
Phase 2 - Product Model: Secondary UoM (F-02 to F-05).
Phase 3 - Sale Order Line: Secondary UoM fields + auto base-qty (F-06 to F-09).
Phase 4 - Delivery / Invoice sync + Validation (F-10 to F-12).

Highlights:
- "Need Secondary UoMs" toggle and a "Secondary UoM's" table on the product
  form, edited through a popup wizard. Each line stores a UoM and its ratio.
- Sale order lines show Secondary UoM + Secondary Qty next to the base
  Quantity/Unit; the base ordered quantity is auto-derived (qty x ratio).
- Deliveries and invoices use the correct base quantity; the invoice line also
  records the secondary UoM reference.
- Validation rejects duplicate or invalid secondary UoMs.

Implements features F-01 to F-12 of the blueprint.
""",
    'website': 'https://inomerp.in',
    'author': 'InomERP',
    'license': 'LGPL-3',
    "depends": [
        "sale_management",
        "account",
        "mail",
        "uom",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/secondary_uom_wizard_views.xml",
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/report_invoice_document_views.xml",
    ],
    'images': ['static/description/banner.png'],
    "installable": True,
    "application": False,
    "auto_install": False,
}
