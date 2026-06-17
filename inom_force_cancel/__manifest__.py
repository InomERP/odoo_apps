# -*- coding: utf-8 -*-
{
    'name': 'Force Cancel Sale & Manufacturing Orders | Automatic Sales and Manufacturing Order Cancellation',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Force cancel confirmed sale orders and completed manufacturing '
               'orders together with their deliveries, invoices and work orders.',
    'description': """
Force Cancel Sale & Manufacturing Orders
========================================

Lets an authorised user cancel orders that Odoo normally locks once they are
processed:

* Cancel a sale order even after its delivery has been validated. The related
  delivery transfer is cancelled and the stock is returned to its original
  location.
* Cancel and reset the related customer invoice, automatically breaking any
  payment reconciliation first.
* Cancel a manufacturing order even when it is already done, including its
  finished work orders and validated component / finished-product moves. The
  produced quantity is reverted back to stock.

A per-user switch ("Allow Force Cancellation") controls who is able to use the
feature, so the action is never exposed to every user by default.
    """,
    'author': 'InomERP',
    'company': 'InomERP',
    'maintainer': 'InomERP',
    'website': 'https://www.inomerp.in',
    'license': 'OPL-1',
    'depends': [
        'sale_management',
        'sale_stock',
        'mrp',
        'stock',
        'account',
        'mail',
    ],
    'data': [
        'views/res_users_views.xml',
        'views/sale_order_views.xml',
        'views/mrp_production_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
