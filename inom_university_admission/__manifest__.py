# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - Admission & Enrollment",
    "version": "17.0.1.5.0",
    "category": "Education",
    "summary": "Phase 2: public admission pipeline, applicant portal, quota / "
               "seat allocation and one-click enrolment for the University "
               "Management System.",
    "description": """
University Management System - Phase 2 (Admission & Enrollment)
==============================================================

Delivers the public-facing admission pipeline on top of the Phase 1
academic core:

* Configurable admission rounds with start / end dates and waitlist.
* Public website enquiry / application form with auto-sequenced
  application numbers (round-aware prefix).
* Stage-based, drag-and-drop kanban pipeline (Enquiry -> Application ->
  Document Verification -> Merit / Entrance -> Offer -> Fee -> Enrolled).
* Document upload with verification checklist and approver sign-off.
* Merit / entrance scoring with bulk CSV import.
* Quota / category seat caps with live availability counters.
* Digital, QR-verifiable offer letters and admission-fee tracking.
* One-click conversion of confirmed applicants into univ.student.
* Applicant self-service portal (status, documents, offer acceptance).
* Automated stage-transition, offer and welcome e-mails.
* Admission funnel dashboard and operational reports.

All code, comments and technical strings are in English. Built for
Odoo 17 conventions (security groups, tree views,
self-closing chatter, no res.partner.mobile).
""",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "OPL-1",
    "depends": [
        "inom_university_core",
        "website",
        # Phase 1: standard Odoo self-service portal account creation
        # (/web/signup). Surfaced on the admission form only; no custom auth.
        "auth_signup",
        # Phase 2: configurable outbound SMS notifications (sms.template).
        "sms",
    ],
    "data": [
        "security/univ_admission_security.xml",
        "security/ir.model.access.csv",
        "data/univ_admission_sequence.xml",
        "data/univ_applicant_stage_data.xml",
        "data/univ_applicant_stage_phase1.xml",
        "data/univ_quota_data.xml",
        "data/univ_document_requirement_template_data.xml",
        "data/univ_mail_templates.xml",
        "data/univ_phase2_mail_templates.xml",
        "data/univ_phase3_mail_templates.xml",
        "data/univ_sms_templates.xml",
        "data/univ_phase2_config.xml",
        "data/univ_phase3_config.xml",
        "data/univ_admission_cron.xml",
        "data/univ_phase3_cron.xml",
        "views/univ_applicant_stage_views.xml",
        "views/univ_admission_round_views.xml",
        "views/univ_admission_round_phase3_views.xml",
        "views/univ_quota_views.xml",
        "views/univ_quota_seat_views.xml",
        "views/univ_applicant_offer_views.xml",
        "views/univ_applicant_views.xml",
        "views/univ_admission_phase1_views.xml",
        "views/univ_applicant_condition_views.xml",
        "views/res_config_settings_views.xml",
        "views/univ_document_requirement_template_views.xml",
        "views/univ_program_views.xml",
        "views/univ_auth_templates.xml",
        "views/univ_admission_dashboard_views.xml",
        "views/univ_admissions_dashboard_action.xml",
        "wizards/univ_merit_import_wizard_views.xml",
        "wizards/univ_applicant_reject_wizard_views.xml",
        "wizards/univ_assign_documents_wizard_views.xml",
        "wizards/univ_document_preview_views.xml",
        "report/univ_admission_report_actions.xml",
        "report/univ_offer_letter_report.xml",
        "report/univ_application_receipt_report.xml",
        "report/univ_quota_utilisation_report.xml",
        "report/univ_doc_pending_report.xml",
        "views/univ_admission_website_templates.xml",
        "views/univ_admission_portal_templates.xml",
        "views/univ_admission_phase1_templates.xml",
        "views/univ_admission_phase2_templates.xml",
        "views/univ_admission_menus.xml",
        "views/univ_notification_log_views.xml",
    ],
    "demo": [
        "demo/univ_admission_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "inom_university_admission/static/src/scss/admission_portal.scss",
        ],
        "web.assets_backend": [
            "inom_university_admission/static/src/scss/admissions_dashboard.scss",
            "inom_university_admission/static/src/js/admissions_dashboard.js",
            "inom_university_admission/static/src/xml/admissions_dashboard.xml",
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
