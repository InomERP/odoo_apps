# -*- coding: utf-8 -*-
{
    "name": "Inom Invoice & Bill Price History",
    "version": "18.0.2.1.0",
    "category": "Sales/Purchase",
    "summary": "View previous invoice and bill price history directly on "
               "sale order and purchase order product lines.",
    "description": """
Invoice & Bill Price History
============================
Adds a history icon on Sale Order / Quotation and Purchase Order / RFQ
product lines. With a single click, users can review previous Customer
Invoices or Vendor Bills for the same partner and product combination,
including date, quantity, unit price, subtotal and document state.
""",

    "keywords": [
        "price history", "invoice price history", "bill price history",
        "customer invoice history", "vendor bill history",
        "last purchase price", "last sale price", "previous price",
        "product price history", "sale order price history",
        "purchase order price history", "quotation price history",
        "rfq price history", "price comparison", "last invoiced price",
        "all in one price history",
    ],
    'author': 'InomERP',
    'support': 'info@inomerp.in',
    'website': 'https://inomerp.in',
    'license': 'LGPL-3',
    "depends": [
        "sale_management",
        "purchase",
        "account",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/views/invoice_history_wizard_view.xml",
        "wizards/views/bill_history_wizard_view.xml",
        "wizards/views/product_price_history_report_wizard_view.xml",
        "reports/sale_cost_down_report_action.xml",
        "reports/templates/sale_cost_down_template.xml",
        "reports/product_price_history_report_action.xml",
        "reports/templates/product_price_history_pdf_template.xml",
        "views/sale_order_view.xml",
        "views/purchase_order_view.xml",
        "views/product_template_view.xml",
        "views/product_price_history_graph_view.xml",
        "views/inventory_menu.xml",
    ],
    "images": ["static/description/banner.png"],
    "application": False,
    "installable": True,
    "auto_install": False,
}
