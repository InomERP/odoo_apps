{
    "name": "Timesheet Backdate Restriction",
    "version": "18.0.1.0.0",

    "summary": "Restrict users from creating backdated timesheet entries",

    "description": """
            Timesheet Backdate Restriction - InomERP
            =========================================

            A professional timesheet management and restriction module by InomERP
            that prevents users from creating or editing backdated timesheet entries.

            Key Features
            ----------------
            - Restrict backdated timesheet entry creation
            - Prevent editing of old timesheet records
            - Enable or disable restrictions from settings
            - Improve timesheet accuracy and compliance
            - Easy configuration with minimal setup
            - Supports employee and project-based workflows

            Business Use Cases
            ---------------------
            - Prevent late or manipulated timesheet submissions
            - Maintain accurate work tracking records
            - Enforce HR and company timesheet policies
            - Improve project billing transparency

            Technical Highlights
            -----------------------
            - Built for Odoo 19
            - Seamlessly integrates with Odoo Timesheets
            - Lightweight and optimized implementation
            - Developer-friendly and scalable architecture

            About InomERP
            ----------------
            InomERP delivers custom Odoo solutions, enterprise modules, and scalable
            business automation tools tailored for modern businesses.
            """,

    "category": "Human Resources",

    "author": "InomERP",
    "website": "https://inomerp.in",
    "license": "LGPL-3",
    "depends": [
        "hr_timesheet",
    ],

    "data": [
        "views/res_config_settings_view.xml",
    ],

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": True,
    "auto_install": False,
}
