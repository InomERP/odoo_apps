{
    "name": "inom Advanced Email Control (CC / BCC)",
    "version": "1.0.0",
    "summary": "Manage CC, BCC, and Reply-To with defaults & tracking in Odoo",
    "description":"""global email cc, global email bcc, odoo email cc, odoo email bcc,email,cc,bcc,odoo email,email odoo,cc and bcc will add , """,

    "category": "Mail",
    "author": "InoMerp",
    "website": "https://www.inomerp.com",
    "depends": [
        "base",
        "mail"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_compose_view.xml",
        "views/res_config_settings_view.xml",
    ],
    "installable": True,
    "application": False,
}
