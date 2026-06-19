# -*- coding: utf-8 -*-
{
    'name': 'Inom Employee Offboarding Management',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Manage employee offboarding with a multi-level resignation '
               'and relieving approval workflow.',
    'description': """
Employee Offboarding Management
===============================
Provides a structured offboarding process for employees leaving the company.

Key capabilities:
    * Employees raise an offboarding request and submit it to their manager.
    * Multi-level approval: reporting manager, then HR.
    * Notice period and relieving date are set during the process.
    * Configurable offboarding reasons.
    * Configurable clearance checklist with progress tracking.
    * Rejection captures a documented reason.
    * Printable offboarding request as a PDF report.
    * Dedicated security roles for coordinators and HR.
    * On relieving, the employee record is archived automatically.
    """,
    'author': 'InomERP',
    'company': 'InomERP Pvt Ltd',
    'maintainer': 'InomERP',
    'website': 'https://www.inomerp.in',
    'license': 'OPL-1',
    'depends': [
        'base',
        'mail',
        'hr',
    ],
    'data': [
        'security/offboarding_security.xml',
        'security/ir.model.access.csv',
        'data/offboarding_sequence.xml',
        'data/offboarding_checklist_data.xml',
        'data/mail_template_data.xml',
        'views/offboarding_reason_views.xml',
        'views/offboarding_checklist_views.xml',
        'views/offboarding_request_views.xml',
        'wizard/offboarding_reject_wizard_views.xml',
        'report/offboarding_report.xml',
        'report/offboarding_report_templates.xml',
        'views/offboarding_menus.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
