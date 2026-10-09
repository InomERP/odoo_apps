# -*- coding: utf-8 -*-
{
    'name': 'Inom Sale Order Merge',
    'version': '20.0.1.0.0',
    'category': 'Sales',
    'summary': 'Merge multiple sale orders and consolidate duplicate order lines in one click',
    'description': """
Sale Order Merge
=================

Merge multiple quotations for the same customer into a single order, and
automatically consolidate duplicate order lines - all from clean, guided
wizards inside Sales.

Key Features
------------

* **Merge Sale Orders** - select multiple quotations from the list view and
  merge them into a new order, or into one of the selected orders.

* **Merge Sale for Same Customer** - pick a customer first and all of their
  draft/sent quotations are auto-loaded, ready to merge.

* **Merge with Different Customer** - optionally merge orders across
  customers into a single new order.

* **Merge Order Lines** - consolidate duplicate lines (same product, price,
  discount and taxes) on a single order into one line with summed quantity.

* **Auto Merge Sale Order Lines** - a Sales Settings toggle that merges
  duplicate lines automatically whenever an order is created or edited.

* Full state validation (only Draft/Sent quotations are merged) and source
  tracking via chatter log messages on every merged order.

Configuration
-------------

Go to **Sales > Configuration > Settings > Quotations & Orders** and enable
**Auto Merge Sale Orderlines** to turn on automatic line consolidation.
""",
    'author': 'InomERP',
    'company': 'InomERP',
    'maintainer': 'InomERP',
    'website': 'https://www.inomerp.in',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'account',
        'mail',
    ],
    'data': [
        'security/ir.access.csv',
        'wizard/sale_order_merge_wizard_views.xml',
        'wizard/sale_order_merge_same_customer_wizard_views.xml',
        'wizard/sale_order_merge_lines_wizard_views.xml',
        'wizard/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 5.0,
    'currency': 'USD',
}