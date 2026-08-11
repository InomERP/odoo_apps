# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.
{
    'name': 'INOM Smart Credit Limit Pro',
    'version': '17.0.1.1.2',
    'category': 'Sales/Sales',
    'summary': 'Customer Credit Limit | Credit Control & Scoring | Auto Credit Hold | Credit Management',
    'description': """
INOM Smart Credit Limit
=======================
Intelligent customer credit control for Odoo:

* Set a smart credit limit per customer with live exposure tracking
  (open receivables + uninvoiced confirmed sale orders).
* Warn or Block sale order confirmation when the limit is exceeded,
  with a manager approval / override flow (audit trailed).
* Smart Credit Score (0-100) computed from payment behaviour, with
  automatic suggested-limit reviews.
* Aging based automatic credit hold and automatic release.
* Enforcement matrix across the document chain: Sale Order,
  Delivery validation and Invoice posting.
* Temporary credit extensions with automatic expiry.
* Full credit audit log of every warn / block / hold / override event.
""",
    'author': 'InomERP',
    'website': 'https://inomerp.in',
    'support': 'info@inomerp.in',
    'license': 'OPL-1',
    'depends': [
        'sale_management',
        'account',
        'stock',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/credit_extension_views.xml',
        'views/credit_audit_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/credit_check_wizard_views.xml',
        'views/menus.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
