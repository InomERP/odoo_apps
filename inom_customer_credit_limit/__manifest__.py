{
    "name": "Inom Customer Credit Limit",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Set customer credit limits and automatically block sales orders "
               "that exceed available credit, with a built-in approval workflow.",
    "description": """
Customer Credit Limit Management
=================================

Manage customer credit risk directly inside Odoo Sales. Set a credit limit
per customer, track outstanding receivables and confirmed sale orders in
real time, and automatically prevent sales orders from being confirmed when
they exceed the customer's available credit.

When an order exceeds the limit, a credit approval request is created with
a complete exposure snapshot. Designated Credit Approval Managers get
notified via chatter, inbox activity, and email - they can approve or
reject directly from the sales order, with a mandatory reason captured on
rejection. Approved orders confirm automatically; rejected ones stay
editable for resubmission.

Key Features
------------
* Per-customer credit limit, used credit, and available credit tracking
* Automatic credit exposure calculation (open invoices + confirmed orders
  + current order)
* Blocks order confirmation when the credit limit is exceeded
* One-click "Request Approval" workflow with full audit trail
* Dedicated Credit Approval Manager security group
* Email notifications and inbox activities for approvers
* Credit status visible on the sales order with a dedicated status bar
* Full chatter log of every approval/rejection decision

Keywords: credit limit, customer credit, credit control, credit approval,
sales credit check, outstanding receivables, credit management, accounts
receivable, order approval workflow, credit risk, B2B credit, AR credit
limit.
    """,
    'author': 'InomERP',
    'support': 'info@inomerp.in',
    'website': 'https://inomerp.in',
    'license': 'LGPL-3',
    "depends": ["sale_management", "account", "mail"],
    "data": [
        "security/credit_approval_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/mail_template_data.xml",
        "views/res_partner_views.xml",
        "views/credit_approval_request_views.xml",
        "views/sale_order_views.xml",
        "wizard/sale_credit_limit_wizard_views.xml",
        "wizard/credit_approval_reject_wizard_views.xml",
    ],
    'images': ['static/description/banner.png'],
    "installable": True,
    "application": False,
    'auto_install': False,
}