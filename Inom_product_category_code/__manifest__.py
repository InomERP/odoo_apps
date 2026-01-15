{
    'name': 'Inom Product Category Code & Mandatory Invoice Reference',
    'version': '17.0.1.0',
    'category': 'Inventory/Accounting',
    'summary': 'Product category code and mandatory customer reference on invoices',
    'description': """
This module enhances Odoo Inventory and Accounting by adding a Code
field to Product Categories and enforcing Customer Reference as
mandatory on Customer Invoices.

It also prevents deletion of posted customer invoices, ensuring
better accounting control, compliance, and data integrity.

Key Features:
• Add Code field to Product Categories  
• Display Category Code in Product Category form  
• Make Customer Reference mandatory for Customer Invoices  
• Block invoice posting without Customer Reference  
• Prevent deletion of posted Customer Invoices  
• Seamless integration with Accounting and Inventory modules  
• Compatible with Odoo 17  

Ideal for businesses that require structured product categorization
and strict invoice validation for accurate accounting.
""",
    'website': 'https://inomerp.in/',
    'author': 'InomERP',
    'depends': ['account', 'stock'],
    'data': [
        'views/product_category_view.xml',
        'views/account_move_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}

