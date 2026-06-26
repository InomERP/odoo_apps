# -*- coding: utf-8 -*-
from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    attach_purchase_documents = fields.Boolean(
        string='Attach Product / Vendor Documents',
        help="When enabled, product and vendor documents are automatically "
             "attached to Request for Quotation / Purchase Order emails sent "
             "with this template.",
    )
