# -*- coding: utf-8 -*-
{
    'name': 'Inom Sale Order Versioning',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Create and manage multiple versions of quotations and sale orders '
               'with a clear version history.',
    'description': """
Sale Order Versioning
=====================
Create multiple versions of a quotation or sale order directly from the order
form. Each new version is a fresh draft copy of the source order that keeps a
clear link back to the original, so the full history of changes stays available.
Highlights
----------
* Generate a new version from the order header with a single click.
* Every version is linked to the original order and numbered sequentially.
* A smart button gives quick access to all versions in the same chain.
* Compare two versions side by side to see what changed.
* A revision reason is recorded each time a version is created.
* A Sales setting controls whether the list shows every version or only the
  latest version of each chain.
* Optionally auto-cancel earlier confirmed versions when a newer one is confirmed.
""",
    'author': 'InomERP',
    'maintainer': 'InomERP',
    'company': 'InomERP',
    'website': 'https://www.inomerp.in',
    'license': 'LGPL-3',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/version_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}