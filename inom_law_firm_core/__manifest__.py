# -*- coding: utf-8 -*-
{
    'name': 'Inom Law Firm - Core',
    'version': '17.0.1.0.0',
    'category': 'Services/Law Firm',
    'summary': 'Core configuration, clients, cases/matters and lawyer profiles — the free foundation of the INOM Law Firm suite.',

    'author': 'InomERP',
    'website': 'https://inomerp.in',
    'support': 'info@inomerp.in',
    'license': 'OPL-1',

    'depends': [
        'base_setup',
        'mail',
        'contacts',
        'hr',
    ],

    'data': [
        'security/law_firm_security.xml',
        'security/inom_law_firm_lawyer_security.xml',
        'security/law_case_security.xml',
        'security/ir.model.access.csv',

        'data/law_firm_sequence.xml',
        'data/law_case_stage_data.xml',

        'views/law_practice_area_views.xml',
        'views/law_case_type_views.xml',
        'views/law_case_stage_views.xml',
        'views/law_case_tag_views.xml',
        'views/law_branch_views.xml',
        'views/res_config_settings_views.xml',
        'views/law_firm_menus.xml',
        'views/res_partner_views.xml',
        'views/law_client_category_views.xml',
        'views/inom_law_firm_client_menus.xml',
        'views/law_specialization_views.xml',
        'views/hr_employee_views.xml',
        'views/inom_law_firm_lawyer_menus.xml',
        'views/law_case_views.xml',
        'views/case_hr_employee_views.xml',
        'views/case_res_partner_views.xml',
        'views/inom_law_firm_case_menus.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
