{
    'name': 'University — Fees',
    'summary': 'Fee structures, components, instalment schedules, scholarships '
               'and student fee accounts built on Odoo accounting.',
    'description': """
University Management System — Fees
===================================
Course and programme fees: structures per programme, quota and academic year,
component-level heads of fee, stored instalment schedules, scholarships and
waivers, and a per-student fee account.

The money itself stays in Odoo accounting. Invoices are account.move records
and payments are account.payment records, so the fee ledger and the trial
balance can never disagree. This module schedules and explains what is owed;
accounting records it.

Install only if the university bills fees through this system. Nothing else
depends on it.
""",
    "version": "20.0.1.0.0",
    'category': 'Education',
    'license': 'LGPL-3',
    # account and account_payment are declared directly rather than relied on
    # transitively: a dependency that resolves by accident today breaks on the
    # first install where the other module is absent.
    'depends': ['inom_portal', 'inom_student', 'account', 'account_payment'],
    'data': [
        'security/inom_fee_rules.xml',
        'reports/fee_receipt.xml',
        'reports/fee_structure.xml',
        'reports/fee_account.xml',
        'data/portal_data.xml',
        'data/notification_data.xml',
        'data/backend_menu_build.xml',
        'security/ir.access.csv',
    ],
    'installable': True,
}
