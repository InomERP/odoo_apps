{
    "name": "Inom POS Receipt Designer",
    "version": "19.0.1.0.0",
    "summary": "Dynamic POS receipt templates with multi-design support",
    "description": """
            POS Receipt Designer - InomERP
            ==============================

            A professional Point of Sale enhancement module by InomERP that enables
            multiple receipt layouts with dynamic configuration per POS.

            Key Features
            ---------------
            - Multiple built-in receipt templates:
                • Classic
                • Modern
                • Compact
                • Detailed

            - Configure different receipt designs per POS session
            - Fully compatible with:
                • On-screen receipt preview
                • Thermal/printed receipts

            - Clean, responsive and professional UI
            - Easy to extend for custom branding and layouts

            Business Use Cases
            ---------------------
            - Multi-store retail businesses with different branding
            - Restaurants needing compact or detailed receipts
            - Custom invoice-style POS receipts for premium customers

            Technical Highlights
            -----------------------
            - Built for Odoo 19 POS (OWL framework)
            - Extends OrderReceipt component using modern overrides
            - Optimized asset loading for performance
            - Developer-friendly and scalable architecture

            About InomERP
            ----------------
            InomERP delivers custom Odoo solutions, enterprise modules, and scalable
            business automation tools tailored for modern businesses.
            """,
    "category": "Sales/Point of Sale",
    "author": "InomERP",
    "website": "https://inomerp.in",   # change if needed
    "maintainer": "InomERP",
    "license": "LGPL-3",

    "price": 0.0,
    "currency": "USD",

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
            "inom_pos_receipt_designer/static/src/overrides/components/order_receipt/order_receipt.js",
            "inom_pos_receipt_designer/static/src/overrides/components/order_receipt/order_receipt.xml",
            "inom_pos_receipt_designer/static/src/overrides/components/order_receipt/order_receipt.scss",
        ],
    },

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": True,
    "auto_install": False,
}
