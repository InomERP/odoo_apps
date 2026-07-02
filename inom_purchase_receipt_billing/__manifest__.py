# -*- coding: utf-8 -*-
{
    'name': 'Inom Vendor Bill from Validated Receipts',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Generate draft vendor bills directly from validated receipts, '
               'including partial deliveries, backorders and multi-PO consolidation.',
    'description': """
Create Vendor Bill from Receipts
================================

This module lets purchase users build a draft vendor bill from one or more
validated receipts instead of from the whole purchase order. It is designed for
real-world procurement where goods arrive in partial shipments and vendor
invoices do not map cleanly onto a single purchase order.

Key features
------------
* Pick the exact received quantities to bill from each receipt (incoming
  picking), including partial deliveries and backorders.
* Consolidate receipts of several purchase orders for the same vendor into a
  single draft bill.
* Billed quantities are matched against what was actually received, preventing
  over-billing.
* Fully integrated with the native purchase / accounting link: the standard
  "Billed" quantity and "Bills" smart button on the purchase order keep working.
""",
    'author': 'InomERP',
    'company': 'InomERP Pvt Ltd',
    'maintainer': 'InomERP',
    'website': 'https://inomerp.in',
    'support': 'info@inomerp.in',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'purchase_stock',
        'stock',
        'account',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_receipt_bill_wizard_views.xml',
        'views/purchase_order_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
