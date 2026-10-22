{
    'name': 'Real Estate Rental Management - Website',
    'version': '19.0.1.6.0',
    'category': 'Website/Website',
    'summary': 'Publish properties on your website and receive enquiries in CRM',
    'description': """
Website for Real Estate Rental Management
=========================================
Public property listing with search and filters, property detail pages with images,
shareable brochure links, an interactive 3D view of each property, and an enquiry form that
creates CRM enquiries.
""",
    'author': 'INOM ERP',
    'website': 'https://www.inomerp.in',
    'license': 'LGPL-3',
    'depends': ['inom_rental_management', 'website_crm'],
    'data': [
        'views/property_property_views.xml',
        'views/crm_lead_views.xml',
        'views/property_templates.xml',
        'data/website_menu_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'inom_rental_management_website/static/src/property_3d/property_3d_materials.js',
            'inom_rental_management_website/static/src/property_3d/property_3d_builder.js',
            'inom_rental_management_website/static/src/property_3d/property_3d_interior.js',
            'inom_rental_management_website/static/src/property_3d/property_3d_walk.js',
            'inom_rental_management_website/static/src/property_3d/property_3d.js',
            'inom_rental_management_website/static/src/property_3d/property_3d.scss',
            'inom_rental_management_website/static/src/property_request/property_request.js',
        ],
    },
    'demo': [
        'data/website_demo.xml',
    ],
    'installable': True,
    'application': False,
}
