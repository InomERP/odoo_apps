# -*- coding: utf-8 -*-
{
    'name': 'INOM Rental Management Suite',
    'version': '19.0.1.0.0',
    'category': 'Services/Real Estate',
    'summary': 'Complete Real Estate Rental, Sales, Website and Maintenance Management Suite',

    'description': """
INOM Rental Management Suite
============================

A complete real estate management solution that combines rental operations,
property sales, website listings, and maintenance management in one suite.

KEY FEATURES
------------

1. Real Estate Rental Management
   - Property and unit management
   - Property owner and tenant management
   - Rental contracts and lease tracking
   - Rent invoicing and payment tracking
   - Security deposit management
   - Property sales and CRM enquiry management
   - Dashboards and business reports

2. Real Estate Rental Management - Website
   - Public property listings
   - Property search and filtering
   - Detailed property pages
   - Property brochure links
   - Website enquiry forms
   - CRM enquiry integration

3. Real Estate Rental Management - Maintenance
   - Property maintenance requests
   - Maintenance tracking linked to properties and leases
   - Maintenance cost tracking
   - Tenant or owner maintenance cost recharge

PRICING
-------

Price: $80 USD

This suite is intended to provide a unified installation entry point
for the INOM real estate rental management modules.

TECHNICAL INFORMATION
---------------------

Technical Name: inom_rental_management_suite
Odoo Version: 19.0
License: LGPL-3

Note:
The suite depends on the three modules listed below. Those modules
must be available in the addons path and compatible with Odoo 19.
""",

    'author': 'INOM ERP',
    'website': 'https://www.inomerp.in',
    'license': 'LGPL-3',

    'price': 80.00,
    'currency': 'USD',

    'depends': [
        'inom_rental_management',
        'inom_rental_management_website',
        'inom_rental_management_maintenance',
    ],

    'data': [],

    'installable': True,
    'application': True,
    'auto_install': False,
}
