{
    "name": "Inom Advanced Email Control (CC / BCC)",
    "version": "1.0.0",
    "summary": "Manage CC, BCC, and Reply-To with defaults & tracking in Odoo",
    "description": """
Advanced Email Control Module for Odoo
--------------------------------------

This module enhances Odoo's email functionality by providing **complete control over CC, BCC, and Reply-To fields**. It allows companies and users to set **default CC/BCC recipients**, ensuring important stakeholders are always included automatically. Additionally, the module provides **Reply-To customization** for outgoing emails, ensuring replies are directed to the correct inbox.

Key Features:
-------------
- **Default CC/BCC**: Automatically include default recipients for all outgoing emails.
- **Reply-To Control**: Customize Reply-To addresses per user or company settings.
- **Email Tracking**: Logs emails automatically in the chatter for easy tracking and auditing.
- **Seamless Odoo Integration**: Works with all Odoo models that use mail composition.
- **User-Friendly Settings**: Configure defaults easily in system settings without code.

Ideal For:
----------
- Businesses that need consistent email communication.
- Teams that require email tracking and accountability.
- Companies using Odoo Mail extensively and want automation for CC/BCC.

Website:
--------
Visit [InomERP]() for more modules and support.
""",
    "category": "Mail",
    'license': 'LGPL-3',
    "author": "InomERP",
    "website": "https://inomerp.com",
    "depends": [
        "base",
        "mail"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_compose_view.xml",
        "views/res_config_settings_view.xml",
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
