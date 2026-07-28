# -*- coding: utf-8 -*-
# Part of INOM Sale Order Label Print. See LICENSE file for full copyright
# and licensing details.
{
    'name': 'INOM Sale Order Label Print',
    'version': '19.0.1.2.0',
    'category': 'Sales/Sales',
    'summary': 'Print product labels directly from the Sale Order using '
               'INOM Label Builder',
    'description': """
INOM Sale Order Label Print
============================
Adds a **Print Labels** button to the Sale Order header so warehouse,
retail and sales teams can print product labels in a single click,
without leaving the Sale Order or navigating to the Product screen.

Features
--------
* **Print Labels** button on the Sale Order form header.
* Automatically builds one label line per order line (product, barcode,
  quantity taken from the ordered quantity).
* Opens the standard INOM Label Builder print wizard: pick the label
  template, language, pricelist, output format (PDF / ZPL / DYMO) or
  send straight to a configured printer with Direct Print.
* PDF output prints one label per page: the page is sized exactly to the
  label, so every barcode lands on its own page.
* Respects INOM Label Builder's security groups and per-user allowed
  templates; users without label access simply won't see the button.

This module only adds the Sale Order integration; all label design,
templates and printing logic are provided by the **INOM Label Builder**
module, which is a required dependency.
    """,
    'website': 'https://inomerp.in',
    'author': 'InomERP',
    'support': 'support@inomerp.in',
    'license': 'OPL-1',
    'depends': ['sale', 'inom_label_builder'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
