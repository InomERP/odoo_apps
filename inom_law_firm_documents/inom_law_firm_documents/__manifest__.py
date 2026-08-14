# -*- coding: utf-8 -*-
{
    'name': 'Inom Law Firm - Documents & Knowledge',
    'version': '17.0.1.0.0',
    'category': 'Services/Law Firm',
    'summary': 'Legal document management, evidence chain-of-custody and the legal knowledge base.',
    'author': 'InomERP', 
    'website': 'https://inomerp.in', 
    'license': 'OPL-1',
    'depends': ['inom_law_firm_core'],
    'data': [
        'security/law_document_security.xml',
        'security/law_evidence_security.xml',
        'security/ir.model.access.csv',
        'data/law_document_sequence.xml',
        'data/law_evidence_sequence.xml',
        'views/law_document_views.xml',
        'views/law_case_views.xml',
        'views/inom_law_firm_document_menus.xml',
        'views/law_knowledge_views.xml',
        'views/knowledge_law_case_views.xml',
        'views/law_evidence_views.xml',
        'views/evidence_law_case_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True, 
    'application': False, 
    'auto_install': False,
}

