# -*- coding: utf-8 -*-
{
    'name': 'Inom Smart List View',
    'version': '19.0.1.1.5',
    'category': 'Sales',
    'summary': 'Sale Order and Quotation Lines Detailed View',
    'description': """
Sale Order Line Views
=====================
A centralized, visual and interactive place to track, analyse and manage the
individual product lines of sale orders and quotations - without opening each
order one by one.

* Two menus under Sales > Orders: **Order Line Views** (confirmed orders) and
  **Quotation Line Views** (draft / sent / cancelled).
* Six views for each menu: List, Kanban, Form, Pivot, Graph, Calendar.
* Three related fields: Product Image, Customer Email, Customer Phone.
* List shows ordered / delivered / invoiced / to-invoice quantities, subtotal
  and a colour status badge, with product image thumbnails.
* Advanced search, custom filters, group by, customer-wise colour calendar,
  graph and pivot analysis.
* Views are READ ONLY - no create / edit / delete / duplicate from these
  screens (editing is done from the original Sale Order form).
""",
    'author': 'InomERP',
    'website': 'https://inomerp.in',
    'license': 'LGPL-3',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_line_views.xml',
        'views/quotation_line_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inom_smart_list_view/static/src/scss/sale_order_line.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
