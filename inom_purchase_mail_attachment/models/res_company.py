# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_mail_attach_enabled = fields.Boolean(
        string='Auto Attach Purchase Documents',
        default=True,
        help="Master switch for auto-attaching product and vendor documents "
             "to purchase emails.",
    )
    purchase_mail_attach_mode = fields.Selection(
        selection=[
            ('all', 'All product documents (except those marked "Never")'),
            ('tagged', 'Only documents marked "Always"'),
        ],
        string='Product Document Mode',
        default='all',
        help="Defines which product documents are attached by default when a "
             "document is set to 'Follow Global Setting'.",
    )
    purchase_mail_attach_vendor_docs = fields.Boolean(
        string='Include Vendor Documents',
        default=True,
        help="Also attach documents configured on the vendor record.",
    )
    purchase_mail_attach_max_count = fields.Integer(
        string='Max Attachment Count',
        default=20,
        help="Maximum number of documents auto-attached to a single purchase "
             "email. Set 0 to disable the guard.",
    )
    purchase_mail_attach_max_mb = fields.Float(
        string='Max Total Attachment Size (MB)',
        default=25.0,
        help="Auto attachments are skipped once the total size of attached "
             "documents would exceed this limit. Set 0 to disable the guard.",
    )
