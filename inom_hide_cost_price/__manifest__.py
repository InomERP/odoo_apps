{
    "name": "Inom Hide Product Cost Price",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Restrict visibility of product cost price based on user permissions",
    "description": """
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
• Fully compatible with Odoo 19
""",
    "author": "InomERP",
    "website": "https://inomerp.in/",
    "license": "LGPL-3",
    "depends": [
        "product",
        "stock"
    ],
    "data": [
        "security/security.xml",
        "views/product_view.xml",
    ],
    "installable": True,
    "application": True,
}

