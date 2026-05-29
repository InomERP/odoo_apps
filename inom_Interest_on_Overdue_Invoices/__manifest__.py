{
    'name': 'inom Interest On Overdue Invoice',
    'version': '17.0.1.0',
    'category': 'Accounting',
    'summary': 'Interest on overdue customer invoices',
'description': """
Overdue Interest on Customer Invoices
======================================

A complete, production-ready engine to calculate and apply interest on
overdue customer invoices in Odoo. Configure flexible rules, preview
the calculation per invoice, post the interest as a Journal Entry or a
Debit Note, and let the cron auto-compute every day.

Key features
------------
* **Flexible Interest Rules** — percentage or flat fee, daily / weekly /
  monthly / yearly periods, grace days, minimum and maximum caps,
  optional flat penalty, simple or compound interest, calculate on
  residual or total invoice amount.
* **Per-Partner & Per-Invoice Overrides** — disable interest for a
  customer, set a partner-specific rule, exclude individual invoices,
  or override the rule for one invoice.
* **Preview & Apply Wizard** — clear two-screen popup: review the full
  breakdown (days overdue, grace, periods, formula) and then apply.
  Choose the output type per use: Journal Entry or Debit Note.
* **Journal Entry Output** — properly booked in a Miscellaneous /
  general journal, with multi-currency support (`currency_id` +
  `amount_currency` preserve the invoice currency).
* **Debit Note Output** — created in the invoice currency with the
  configured interest product, auto-fills analytic distribution to
  satisfy mandatory analytic plans, ready to confirm and post.
* **Overdue Interest Tab** — a dedicated tab on every customer invoice
  shows the interest settings, overdue status, and `Preview Interest` /
  `Apply Interest` action buttons.
* **Smart Buttons** — Interest count + total on customer invoices and
  partners, drilling down to the interest history.
* **Automatic Cron** — daily scheduled action computes overdue interest
  drafts; flip *Auto-Apply Interest* in settings to post automatically.
* **Reporting Menu** — dedicated *Overdue Interest > Interest
  Calculations* report listing every calculation, with filters by
  status, partner, rule and date.
* **Multi-Currency** — interest is computed in the invoice's currency;
  amounts are converted to the company currency for posting while the
  original foreign amount is preserved on the line.
* **Mandatory Analytic Plans** — auto-detects mandatory analytic plans
  on the interest account and assigns a valid 100%% distribution so the
  document can always be confirmed.

Search keywords
---------------
overdue interest, late payment, late fee, dunning, customer invoices,
interest calculation, penalty, finance charge, debit note, journal
entry, automatic interest, daily interest, weekly interest, monthly
interest, yearly interest, compound interest, grace period, accounting,
accounts receivable, AR, collections, Odoo 19, Community.

Compatibility
-------------
Odoo 19 Community / Enterprise. Sibling builds available for Odoo 17
and Odoo 18 with the same feature set.

Support
-------
For installation help, customizations or bug reports, contact the
maintainer at the address in this manifest.
""",
    'author': 'inomERP',
    'depends': ['account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/interest_cron.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/interest_rule_views.xml',
        'views/interest_history_views.xml',
        'views/account_move_views.xml',
        'wizard/apply_interest_wizard_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'key': 'inom_Interest_on_Overdue_Invoices.inom_Interest_on_Overdue_Invoices',
}
