{
    'name': 'Inom Hide Product Cost Price',
    'version': '18.0.1.0',
    'category': 'Inventory',
    'summary': 'Restrict visibility of product cost price based on user permissions',
    'description': """
Hide Product Cost Price module restricts the visibility of product
cost price (standard_price) in Odoo based on user access rights.

The cost price is a sensitive business value and should only be
visible to authorized users such as administrators or accountants.
This module introduces a dedicated user group to control who can
view the product cost price.

Key Features:
• Adds a new security group "View Cost Price"  
• Allows authorized users to view product cost price  
• Hides cost price from unauthorized users  
• Works in Product Form View  
• Works in Product List (Tree) View  
• Improves confidentiality of pricing information  
• Fully compatible with Odoo 18  

This module follows Odoo security best practices and ensures
safe handling of sensitive pricing data.
""",
    'website': 'https://inomerp.in/',
    'live_test_url': 'https://www.youtube.com/watch?v=IJci2E7CACs',
    'author': 'InomERP',
    'depends': ['product'],
    'data': [
        'security/security.xml',
        'views/product_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
