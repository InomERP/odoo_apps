# -*- coding: utf-8 -*-
{
    'name': "Inter Company Stock Transfer",
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': "Automatically create the counterpart receipt or delivery in "
               "another company when an inter company stock operation is "
               "validated.",
    'description': """
Inter Company Stock Transfer
============================

Automate stock movements between companies of the same database at the
warehouse operation level, without requiring a Sale Order or Purchase Order.

When a company validates a Receipt or Delivery whose partner is another
company, an opposite operation (Delivery or Receipt) is created automatically
in that destination company.

Key features
------------
* Trigger directly on stock operations (Receipt / Delivery), no SO/PO needed.
* Per company configuration: enable, choose the operation types and the
  destination warehouse.
* Loop protection: automatically generated operations never trigger a new one.
* Counterpart operations are linked together for easy navigation.
""",
    'author': "InomERP",
    'company': "InomERP",
    'maintainer': "InomERP",
    'website': "https://inomerp.in",
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'mail',
    ],
    'data': [
        'views/res_company_views.xml',
        'views/stock_picking_views.xml',
    ],
    "images": ["static/description/banner.png"],
    'installable': True,
    'application': False,
    'auto_install': False,
}
