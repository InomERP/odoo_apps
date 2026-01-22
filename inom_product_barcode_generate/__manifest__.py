{
	'name': 'Inom Automatic EAN13 Barcode Generator',
	'version': '1.0',
    'category': 'Inventory/Product',
    'summary': 'Automatically generate unique EAN13 barcodes for products',
    'description': """
This module automatically generates unique EAN-13 barcodes for products,
helping businesses manage inventory efficiently and avoid duplicate barcodes.

Key Features:
• Automatic EAN-13 barcode generation on product creation  
• Ensures barcode uniqueness  
• Optional regenerate button on product form  
• Seamless integration with Odoo Inventory  
• Compatible with Odoo 17.  

Ideal for businesses that want fast, reliable, and standardized barcode management.
""",
    'website': 'https://inomerp.in/',
	'author': 'InomERP',
	'depends': ['product', 'stock'],
	'data': [
	    'views/product_template_views.xml',
	],
	'images': ['static/description/banner.png'],
	'license': 'LGPL-3',
	'installable': True,
	'application': True,
}
