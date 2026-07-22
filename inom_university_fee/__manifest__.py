# -*- coding: utf-8 -*-
{
    "name": "Inom University Fees & Finance",
    "version": "18.0.2.3.0",
    "summary": "Fee structures, invoicing, installments, scholarships and "
               "refunds integrated with Odoo Accounting.",
    "description": """
University Management System - Phase 3 (Fees & Finance)
=======================================================
Fee structures, bulk invoicing, online and offline collection, installment
plans, late-fee accrual, defaulter tracking, scholarships, concessions and a
two-level refund workflow with credit notes. No parallel ledger: everything
posts to native Odoo Accounting (account.move / account.payment).
""",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "category": "Education",
    "depends": [
        "inom_university_core",
        "inom_university_admission",
        "account",
        "payment",
        "account_payment",
    ],
    "data": [
        # Security
        "security/univ_fee_security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/univ_fee_sequence.xml",
        "data/univ_fee_data.xml",
        "data/univ_fee_mail_templates.xml",
        "data/univ_fee_cron.xml",
        # Views & actions
        "views/univ_fee_master_views.xml",
        "views/univ_fee_category_head_views.xml",
        "views/univ_fee_structure_views.xml",
        "views/univ_fee_structure_deposit_views.xml",
        "views/univ_applicant_deposit_views.xml",
        "views/univ_fee_invoice_views.xml",
        "views/univ_fee_installment_views.xml",
        "views/univ_fee_refund_views.xml",
        "views/univ_fee_waiver_views.xml",
        "views/univ_scholarship_views.xml",
        "views/univ_fee_wizard_views.xml",
        "views/univ_student_fee_views.xml",
        "views/univ_fee_portal_templates.xml",
        "views/univ_admission_portal_deposit_templates.xml",
        # Reports (actions referenced by menus)
        "report/univ_fee_report_actions.xml",
        "report/univ_fee_receipt_templates.xml",
        "report/univ_fee_statement_templates.xml",
        "report/univ_fee_ledger_templates.xml",
        # Settings
        "views/res_company_views.xml",
        # Menus (last)
        "views/univ_fee_menus.xml",
    ],
    "demo": [
        "demo/univ_fee_demo.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "installable": True,
    "application": False,
}
