{
    "name": "Inom Customer Code & Mandatory Phone",
    "version": "17.0.1.0.0",
    "category": "Contacts",
    "summary": "Enforce unique Customer Code and mandatory Phone number for Contacts",
    "description": """
Inom Customer Code & Mandatory Phone

This module enhances Odoo Contacts by enforcing structured customer
identification and mandatory contact information.

Key Features:
- Adds Customer Code field to Contacts
- Enforces unique Customer Code
- Makes Phone Number mandatory
- Prevents saving records without required values
- Avoids duplicate customer records
- Seamless integration with Odoo Contacts, Sales, and Accounting
""",
    "author": "Inom ERP",
    "website": "https://www.inomerp.in",
    "support": "info@inomerp.in",
    'images': ['static/description/banner.png'],
    "license": "LGPL-3",
    "depends": [
        "base",
        "contacts",
    ],
    "data": [
        "views/res_partner_views.xml",
        "data/customer_sequence_data.xml",
    ],
    "installable": True,
    "application": True,
}


