{
    "name": "Inom POS Receipt Designer",
    "version": "18.0.1.0.0",
    "summary": "Dynamic POS receipt templates with multi-design support",
    "description": """
    POS Receipt Designer | POS Receipt Template | Odoo POS Custom Receipt

    POS Receipt Designer - InomERP

    This module allows you to customize POS receipts in Odoo with multiple
    receipt templates and dynamic design selection per POS configuration.

    Keywords: POS Receipt, Odoo POS Receipt, POS Print, Receipt Template,
    POS Customization, POS Invoice, POS UI, POS Design

    Key Features:
    -------------
    - Multiple POS receipt templates:
        • Classic POS Receipt
        • Modern POS Receipt
        • Compact POS Receipt
        • Detailed POS Receipt

    - Dynamic POS receipt selection per POS configuration
    - Customize POS receipt layout and design easily
    - Supports POS receipt screen preview
    - Supports POS receipt printing (thermal printer ready)

    POS Customization:
    ------------------
    - Change receipt format in POS
    - Customize receipt design per shop
    - Add branding to POS receipts
    - Improve POS UI and customer experience

    Use Cases:
    ----------
    - Retail POS receipt customization
    - Restaurant POS receipt printing
    - Multi-store POS branding
    - Custom POS invoice-style receipts

    Technical Details:
    ------------------
    - Compatible with Odoo 18 POS
    - Built using OWL POS framework
    - Extends OrderReceipt component
    - Lightweight and fast performance

    About InomERP:
    --------------
    InomERP provides Odoo customization, POS development, and business automation solutions.
    """,
    "category": "Sales/Point of Sale",
    "author": "InomERP",
    "website": "https://inomerp.in",   # change if needed
    "maintainer": "InomERP",
    "license": "LGPL-3",


    "depends": [
        "point_of_sale",
        "product"
    ],

    "data": [
        "views/pos_config_views.xml",
        "views/pos_receipt_design_menu.xml",
    ],

    "assets": {
        "point_of_sale._assets_pos": [
            "pos_receipt_designer/static/src/overrides/components/order_receipt/order_receipt.js",
            "pos_receipt_designer/static/src/overrides/components/order_receipt/order_receipt.xml",
            "pos_receipt_designer/static/src/overrides/components/order_receipt/order_receipt.scss",
        ],
    },

    "images": [
        "static/description/banner.png"
    ],

    "installable": True,
    "application": True,
    "auto_install": False,
}