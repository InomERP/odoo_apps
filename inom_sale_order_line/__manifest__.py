{
    'name': 'Inom Sale Order Line - Product Image',
    'version': '17.0.1.0',
    'category': 'Sales/CRM',
    'summary': 'Automatically display product images in sale order lines and reports',
    'description': """
Inom Sale Order Line module automatically displays the product image 
whenever a product is selected in a sale order line, both in form view 
and PDF reports.

Key Features:
• Automatic product image display on sale order line  
• Form view integration for visual reference  
• Sale order PDF report integration  
• Reduces errors and mis-selection of products  
• Seamless integration with Odoo Sale and Product modules  
• Compatible with Odoo 17  

Ideal for businesses that want visual confirmation of products in sales 
orders and reports, improving accuracy and efficiency.
""",
    'website': 'https://inomerp.in/',
    'author': 'InomERP',
    'depends': ['sale', 'product'],
    'data': [
        'views/sale_order_views.xml',
        'reports/sale_order_report.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
