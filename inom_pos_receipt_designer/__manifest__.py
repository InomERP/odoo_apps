{
    "name": "Inom POS Receipt Designer",
    "version": "20.0.1.0.7",
    "summary": "Dynamic POS receipt templates with multi-design support",
    "description": """
        POS Receipt Designer for Odoo 20.
        Select a receipt design per POS configuration and apply it to the
        standard Odoo POS receipt without replacing the core receipt logic.
    """,
    "category": "Sales/Point of Sale",
    "author": "InomERP",
    "website": "https://inomerp.in",
    "maintainer": "InomERP",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "product"],
    "data": [
        "views/pos_config_views.xml",
        "views/pos_receipt_design_menu.xml",
        "receipt/pos_order_receipt.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
