# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - Core",
    "version": "17.0.1.0.0",
    "category": "Education",
    "summary": "Foundation & Academic Core: masters, security, audit, "
               "multi-campus scaffolding for the University Management System.",
    "description": """
University Management System - Phase 1 (Foundation & Academic Core)
==================================================================

Delivers the structural foundation of the University Management System:

* Academic structure: Faculty/School -> Department -> Program -> Batch ->
  Semester -> Section -> Subject (with elective groups and credit hours).
* Student master with document vault, guardians and a draft -> enrolled ->
  active -> graduated/dropped lifecycle.
* Faculty/staff master with designation, qualifications and subject linkage.
* Multi-company / multi-campus data isolation via record rules.
* Full security group hierarchy using layered res.groups and record rules.
* Immutable audit trail mixin for sensitive writes.
* Chatter, activities, kanban, list, form and search views on every master.
* QWeb PDF reports and read-only self-service portal placeholders.

All code, comments and technical strings are in English. Views target
Odoo 17 / 18 / 19 through the list/tree compatibility conventions.
""",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "OPL-1",
    "depends": [
        "base",
        "mail",
        "contacts",
        "portal",
    ],
    "data": [
        "security/univ_security.xml",
        "security/ir.model.access.csv",
        "data/univ_sequence_data.xml",
        "views/univ_faculty_school_views.xml",
        "views/univ_department_views.xml",
        "views/univ_program_views.xml",
        "views/univ_batch_views.xml",
        "views/univ_semester_views.xml",
        "views/univ_section_views.xml",
        "views/univ_subject_elective_group_views.xml",
        "views/univ_subject_views.xml",
        "views/univ_student_views.xml",
        "views/univ_faculty_views.xml",
        "views/univ_audit_log_views.xml",
        "views/res_partner_views.xml",
        "views/univ_dashboard_views.xml",
        "views/univ_portal_templates.xml",
        "views/univ_menus.xml",
        "report/univ_report_actions.xml",
        "report/univ_student_master_report.xml",
        "report/univ_faculty_master_report.xml",
        "report/univ_academic_structure_report.xml",
    ],
    "demo": [
        "demo/univ_demo_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "inom_university_core/static/src/scss/portal.scss",
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
