# -*- coding: utf-8 -*-
{
    'name': 'Inom Product Combo Pack',
    'version': '19.0.1.3.0',
    'category': 'Sales',
    'summary': 'Sell and purchase several products together as one combo pack '
               'with automatic delivery and receipt of the pack items.',
    'description': """
Inom Product Combo Pack
=======================

Combine several products into a single combo pack and use that pack on
sales and purchase orders. The pack can be added in two ways:

* Normal mode: the pack is added as a single order line carrying the pack
  price, while its component products are delivered / received automatically.
* Exploded mode: every component product is added as its own order line with
  its individual price.

Main capabilities
------------------
* Define a combo pack on any product with its own component lines.
* Automatic or manual pack price.
* Combo pack filter on the product views.
* Add combo packs (normal or exploded) on sales orders.
* Automatic delivery of the pack component products.
* Optional combo packs on purchase orders (activated from Purchase settings).
* Automatic receipt of the pack component products.
* Dynamic wizard to choose the pack, quantity and prices before adding it.
    """,
    'author': 'InomERP',
    'company': 'InomERP Pvt Ltd',
    'maintainer': 'InomERP Pvt Ltd',
    'website': 'https://www.inomerp.in',
    'license': 'LGPL-3',
    'depends': [
        'sale_stock',
        'purchase_stock',
        'stock',
        'sale_management',
        'purchase',
        'account',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'wizard/combo_pack_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    
}
