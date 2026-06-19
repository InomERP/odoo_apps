# -*- coding: utf-8 -*-
{
    'name': 'Inom Warehouse Access Control',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Restrict users to authorized warehouse locations with automatic child-location inheritance and Super Warehouse Manager access.',
    'description': """
InomERP Warehouse Access Control
================================
Decide exactly which users can work with which warehouse locations, and let
Odoo automatically enforce that across stock, transfers and operations.

Key Features
------------
* Assign authorized users on each location — or assign locations on each user.
* A location with no authorized user stays global and visible to everyone.
* Authorized users automatically gain access to every child location.
* Restrictions are enforced on locations, on-hand quantities, transfers,
  operation types, stock moves and detailed operations.
* A dedicated "Super Warehouse Manager" right (and the Administrator) bypass
  every restriction.
* Fully compatible with multi-company setups and standard Odoo flows.

Clean & Safe
------------
This module only adds new fields, one security group and record rules. It does
not override or replace any standard Odoo behaviour.
""",
    'author': 'InomERP',
    'maintainer': 'InomERP',
    'company': 'InomERP',
    'website': 'https://www.inomerp.in',
    'support': 'support@inomerp.in',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'security/warehouse_access_groups.xml',
        'security/warehouse_access_rules.xml',
        'views/stock_location_views.xml',
        'views/res_users_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
}
