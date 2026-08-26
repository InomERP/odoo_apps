# -*- coding: utf-8 -*-
# Part of inom_mo_reset. See LICENSE file for full copyright and licensing details.
{
    'name': 'INOM Manufacturing Order Reset to Draft',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Reset cancelled Manufacturing Orders back to Draft in one click '
               'while preserving all data, raw material moves and work orders.',
    'description': """
Manufacturing Order Reset to Draft (inom_mo_reset)
==================================================

Adds a one-click *Set to Draft* capability on **cancelled** Manufacturing
Orders. The original product, Bill of Materials, quantities, dates, responsible
person and notes are preserved. Linked raw material / finished stock moves are
revived to the *Draft* state and all work orders are restored to *To Do*
(ready) so the standard Odoo manufacturing workflow can resume seamlessly.

Key points
----------
* Button is only visible on cancelled orders (clean, confusion-free UI).
* Zero configuration -- install and use.
* Instant, synchronous state change (no scheduled jobs / queues).
* Multi-user concurrent safe.
* Full audit trail via the tracked ``set_to_draft`` flag and chatter logging.
""",
    'website': 'https://inomerp.in',
    'author': 'InomERP',
    'live_test_url': 'https://www.youtube.com/watch?v=08-g52tjTwQ&t=3s',
    'license': 'LGPL-3',
    # mrp transitively brings in `stock` and `mail` (chatter). `stock` is kept
    # explicit per the functional specification. The spec's "discuss" dependency
    # maps to Odoo's `mail` framework (chatter) which mrp already requires.
    'depends': [
        'mrp',
        'stock',
    ],
    'data': [
        'security/mo_reset_security.xml',
        'security/ir.model.access.csv',
        'views/mrp_production_views.xml',
    ],
    "images": [
        "static/description/banner.gif",
        "static/description/icon.png",
        # "static/description/banner.png"
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
