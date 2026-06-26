# -*- coding: utf-8 -*-
{
    'name': 'Inom Purchase Email - Auto Attach Product & Vendor Documents',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Automatically attach product images, brochures, datasheets and '
               'vendor documents to Request for Quotation / Purchase Order emails.',
    'description': """
Auto Attach Product & Vendor Documents on Purchase Emails
=========================================================

Streamline your procurement communication. When you send a Request for
Quotation or a Purchase Order by email, this module automatically appends
the relevant product documents (images, brochures, datasheets, certificates)
of every ordered product directly to the outgoing email - no manual work.

Key features
------------
* Automatic product document attachment on RFQ / PO emails.
* Per mail template switch to enable or disable attachments.
* Granular per-document control: Always / Never / Follow global setting.
* Vendor level documents (NDA, quality terms, onboarding pack) attached too.
* Per-vendor opt-out to skip auto attachments for specific suppliers.
* Global settings with attachment size and count guards to keep emails light.
* Smart button on the Purchase Order to preview the documents that will be sent.

    """,
    'author': 'InomERP Pvt Ltd',
    'company': 'InomERP Pvt Ltd',
    'maintainer': 'InomERP Pvt Ltd',
    'website': 'https://inomerp.in',
    'support': 'info@inomerp.in',
    'license': 'OPL-1',
    'depends': [
        'purchase',
        'mail',
        'product',
    ],
    'data': [
        'data/mail_template_config.xml',
        'views/product_document_views.xml',
        'views/mail_template_views.xml',
        'views/res_partner_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
