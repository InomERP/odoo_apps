# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductDocument(models.Model):
    _inherit = 'product.document'

    attach_on_purchase = fields.Selection(
        selection=[
            ('default', 'Follow Global Setting'),
            ('always', 'Always Attach on Purchase Email'),
            ('never', 'Never Attach on Purchase Email'),
        ],
        string='Purchase Email',
        default='default',
        help="Controls whether this document is attached to outgoing "
             "Request for Quotation / Purchase Order emails:\n"
             "- Follow Global Setting: respect the company-wide attachment mode "
             "defined in Purchase Settings.\n"
             "- Always: attach this document regardless of the global mode.\n"
             "- Never: never attach this document to purchase emails.",
    )
