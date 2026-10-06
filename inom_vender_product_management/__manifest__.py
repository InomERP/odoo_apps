# -*- coding: utf-8 -*-
{
    'name': 'Inom Vendor Product Management ',
    'version': '20.0.3.2.1',
    'category': 'Purchases',
    'summary': 'Vendor product catalog + vendor stock + Excel import wizards',
    'description': """
    Manage everything your suppliers offer in one structured place: each vendor gets 
    its own product catalog with vendor codes, prices and stock levels across unlimited 
    vendor-side warehouses. Link vendor products to your internal product variants, see supplier 
    stock converted to your own unit of measure (with mismatch warnings), and load complete 
    supplier price lists or availability files in seconds using guided Excel import wizards with
      row selection, archive options and a full results/error report. Vendor stock stays purely 
      informational — zero interference with your own inventory, valuation or reservations. Perfect 
      for multi-supplier purchasing teams, make-to-order and drop-shipping businesses.
    """,
    'Keywords' :'vendor product management, supplier catalog, vendor catalog, supplier '
    'price list, vendor pricelist, vendor stock, supplier stock levels, vendor products, '
    'product matching, supplier products, purchase management, procurement, dropshipping stock, '
    'make to order, vendor locations, supplier warehouse, excel import, import vendor prices, import supplier catalog, '
    'uom conversion, vendor price import, purchase odoo 19, supplier management, vendor management odoo',
    "author": "InomERP",
    "website": "https://inomerp.in",
    "support": "info@inomerp.in",    
    "license": "OPL-1",
    'depends': ['purchase', 'mail', 'uom', 'portal'],
    'data': [
        'security/security.xml',
        'security/ir.access.csv',
        'data/vendor_import_templates.xml',
        'data/mail_message_subtype_data.xml',
        'data/portal_entry_data.xml',
        'views/vendor_location_views.xml',
        'views/vendor_stock_views.xml',
        'views/vendor_product_views.xml',
        'wizard/vendor_product_import_wizard_views.xml',
        'wizard/vendor_stock_import_wizard_views.xml',
        'wizard/vendor_import_result_views.xml',
        'wizard/vendor_import_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/portal_templates.xml',
        'views/menus.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    "images": ["static/description/banner.png"],
    'installable': True,
    'application': False,
    'auto_install': False,
     'price': 10.0,
    'currency': 'USD',
}
