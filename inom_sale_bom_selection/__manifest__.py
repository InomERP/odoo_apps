# -*- coding: utf-8 -*-
{
    'name': 'Sale BoM Selection on Sale Order Line',
    'version': '19.0.1.2.0',
    'category': 'Sales/Manufacturing',
    'summary': 'Select a specific Bill of Material (Manufacture or Kit) on each '
               'Sale Order line and carry it forward to the Manufacturing or '
               'Delivery Order.',
    'description': """
Sale BoM Selection on Sale Order Line
=====================================

Extend the Sale Order line with a 'Bill of Material' field so the sales team can
decide exactly which BoM should be used for a product *before* confirming the
order.

Key features
------------
* A 'Bill of Material' field on every Sale Order line, filtered to the BoMs
  linked to the line's product.
* Manufacture (normal) BoM support: the selected BoM is used by the
  Manufacturing Order created on confirmation.
* Kit (phantom) BoM support: the selected Kit BoM is exploded into the correct
  components on the Delivery Order created on confirmation.
* Works on Odoo Community and Enterprise (Online, Odoo.sh and On-Premise).

Keywords
---------
Sale Order Line BoM, Sale Order Bill of Material, Sale Order BoM,
Sale MRP Integration, Odoo Manufacturing, Odoo MRP,
Bill of Material Selection, Kit BoM, Phantom BoM,
Manufacturing Order BoM, Delivery Order BoM,
Multi BoM, Product BoM Selector, Sales Manufacturing Integration,
Odoo Community, Odoo Enterprise, Odoo Online, Odoo.sh,
Odoo On-Premise, Odoo 17, InomERP.

""",
    'website': 'https://inomerp.in',
    'author': 'InomERP',
    'license': 'LGPL-3',
    'depends': [
        'mrp',
        'stock',
        'sale_stock',
        'sale_mrp',
        'mail',
        'account',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
