# -*- coding: utf-8 -*-
{
    'name': 'Inom Multi-Company Email Signatures',
    'version': '17.0.1.0.0',
    'summary': 'Per-company email signature for every user | Multi-Company Signature',
    'description': """
    Multi-Company Email Signatures
    ================================
    * Set different email signatures for each company
    * Draw, Type or Upload signature
    * Auto-switch signature on company change
    * Admin can manage signatures for all users
    * Per-user per-company signature storage
    * Supports Odoo 19 multi-company setup

    Keywords: email signature, multi company signature, per company signature,
    user signature, company email, signature management, email footer,
    multi company, odoo signature, draw signature, upload signature
        """,
    'author': 'InomERP',
    'support': 'info@inomerp.in',
    'website': 'https://inomerp.in',
    'license': 'LGPL-3',
    'category': 'Productivity/Email',
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/res_users_signature_rules.xml',
        'views/res_users_signature_views.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inom_multi_company_email_signatures/static/src/css/signature_widget.css',
            'inom_multi_company_email_signatures/static/src/xml/signature_widget.xml',
            'inom_multi_company_email_signatures/static/src/js/signature_widget.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,

}
