# -*- coding: utf-8 -*-
{
    "name": "Inom University Management - Academics",
    "version": "19.0.2.0.1",
    "category": "Education",
    "summary": "Curriculum, timetable, attendance, examinations, results and "
               "transcripts for the University Management System.",
    "description": """
University Academics (Phase 4)
==============================
Curriculum and syllabus authoring, timetable scheduling with clash detection,
attendance capture with shortage tracking, examination scheduling with hall and
invigilator allocation, mark entry with moderation and re-evaluation, and
credit-weighted SGPA/CGPA results with mark sheets and transcripts. Includes
student, parent and faculty portals, dashboards and reports.
""",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": [
        "inom_university_core",
        "inom_university_admission",
        "inom_university_fee",
        "calendar",
    ],
    "data": [
        "security/univ_academics_security.xml",
        "security/ir.model.access.csv",
        "data/univ_academics_sequence.xml",
        "data/univ_academics_data.xml",
        "data/univ_academics_mail_templates.xml",
        "data/univ_registration_mail_templates.xml",
        "data/univ_academics_cron.xml",
        "views/univ_academics_masters_views.xml",
        "views/univ_academics_wizard_views.xml",
        "views/univ_syllabus_views.xml",
        "views/univ_timetable_views.xml",
        "views/univ_attendance_views.xml",
        "views/univ_exam_views.xml",
        "views/univ_result_views.xml",
        "views/univ_student_academic_views.xml",
        "views/univ_academics_dashboard_views.xml",
        "report/univ_academics_report_actions.xml",
        "report/univ_academics_reports.xml",
        "report/univ_registration_report.xml",
        "views/univ_academics_portal_templates.xml",
        "views/univ_registration_portal_templates.xml",
        "views/univ_academics_menus.xml",
        "views/univ_registration_views.xml",
    ],
    "demo": [
        "demo/univ_academics_demo.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "application": False,
    "installable": True,
}
