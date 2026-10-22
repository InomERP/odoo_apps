{
    'name': 'Real Estate Rental Management',
    'version': '19.0.1.8.0',
    'category': 'Services/Real Estate',
    'summary': 'Manage properties, owners, tenants, rental contracts and property sales',
    'description': """
Real Estate Property Sale and Rental Management
================================================
Properties, owners, tenants and buyers on standard contacts, owner and
tenant documents, property sales from CRM enquiry to booking, invoicing
and sale, rental contracts with renewal and termination, rent invoicing,
security deposits, security groups and reports.
""",
    'author': 'INOM ERP',
    'website': 'https://www.inomerp.in',
    'license': 'LGPL-3',
    'depends': ['mail', 'account', 'crm'],
    'data': [
        'security/rental_management_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
        'data/ir_cron_data.xml',
        'views/property_type_views.xml',
        'views/property_amenity_views.xml',
        'views/property_property_views.xml',
        'wizard/rental_contract_wizard_views.xml',
        'wizard/deposit_settlement_views.xml',
        'wizard/property_enquiry_create_views.xml',
        'views/property_rental_contract_views.xml',
        'views/property_rent_schedule_views.xml',
        'views/property_sale_contract_views.xml',
        'views/property_partner_document_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/crm_lead_views.xml',
        'views/account_move_views.xml',
        'report/property_sale_contract_report.xml',
        'report/rent_report_views.xml',
        'report/property_report_views.xml',
        'views/rental_management_menus.xml',
    ],
    'demo': [
        'data/demo/rental_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inom_rental_management/static/src/dashboard/**/*',
        ],
    },
    'installable': True,
    'application': True,
}
