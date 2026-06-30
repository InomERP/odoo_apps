# -*- coding: utf-8 -*-
{
    'name': 'Inom Smart Inventory Adjustment Approval & Control',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Approval control for inventory adjustments with quantity and '
               'value thresholds, financial impact preview and audit trail.',
    'description': """
Inventory Adjustment Control
============================

Add a configurable approval layer on top of inventory adjustments so that
stock corrections are reviewed before they hit the books.

Key features
------------
* Approval workflow for inventory adjustments (Apply is intercepted).
* Role based permission through a dedicated approver group.
* Color coded approval status (To Approve / Approved / Rejected).
* Activity notifications sent to approvers on every new request.
* Dedicated "Adjustment Approvals" list to review pending requests.
* Bulk approve and bulk reject from the list and form views.
* Threshold based auto-approval: only adjustments above a quantity or value
  limit require approval (small corrections pass through automatically).
* Financial impact preview: the value effect of each adjustment is shown
  while counting and on every approval request.
* Mandatory rejection reason with a full chatter audit trail.
""",
    'author': 'InomERP',
    'company': 'InomERP Pvt Ltd',
    'maintainer': 'InomERP Pvt Ltd',
    'website': 'https://inomerp.in',
    "live_test_url": "https://youtu.be/YC1xp-arK0&t",
    'license': 'OPL-1',
    'depends': ['stock', 'mail'],
    'data': [
        'security/stock_adjust_security.xml',
        'security/ir.model.access.csv',
        'wizard/stock_adjust_reject_wizard_views.xml',
        'views/stock_quant_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
