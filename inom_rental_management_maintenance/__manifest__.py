{
    'name': 'Real Estate Rental Management - Maintenance',
    'version': '19.0.1.3.0',
    'category': 'Supply Chain/Maintenance',
    'summary': 'Property maintenance requests on standard Odoo Maintenance',
    'description': """
Maintenance for Real Estate Rental Management
=============================================
Links standard maintenance requests to properties and leases, adds role-based access,
protects the maintenance history, and tracks costs with optional recharge to the tenant
or owner through standard invoices.
""",
    'author': 'INOM ERP',
    'website': 'https://www.inomerp.in',
    'license': 'LGPL-3',
    'depends': ['inom_rental_management', 'maintenance'],
    'data': [
        'security/maintenance_security.xml',
        'data/product_data.xml',
        'views/maintenance_request_views.xml',
        'views/property_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'data/maintenance_demo.xml',
    ],
    'installable': True,
    'application': False,
}
