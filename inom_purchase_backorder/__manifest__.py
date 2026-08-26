# -*- coding: utf-8 -*-
# Part of Inomerp. See LICENSE file for full copyright and licensing details.
{
    'name': 'Inom Purchase Backorder Status',
    'version': '17.0.1.5.0',
    'category': 'Purchases',
    'summary': 'Flag purchase orders that still have an outstanding (pending) backorder receipt.',
    'description': """
Purchase Backorder Status
=========================

Track whether a Purchase Order still has an outstanding (pending) backorder
receipt, directly from the Purchase Order list and form views, with a dedicated
search filter. The indicator clears automatically once every backorder receipt
has been fully validated.

This release provides the complete feature set: the backorder status field,
the list view indicator, the form view badge and the search filter.
    """,
    'author': 'InomERP',
    'website': 'https://inomerp.in',
    'support': 'info@inomerp.in',
    'license': 'OPL-1',
    'live_test_url': 'https://www.youtube.com/watch?v=D_G_aw3V3Og',
    'depends': [
        'purchase',
        'stock',
        'purchase_stock',
        'account',
        'mail',
    ],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
