# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_mail_attachment_enabled = fields.Boolean(
        related='company_id.purchase_mail_attach_enabled',
        readonly=False,
        string='Auto Attach Purchase Documents',
    )
    purchase_mail_attachment_mode = fields.Selection(
        related='company_id.purchase_mail_attach_mode',
        readonly=False,
        string='Product Document Mode',
    )
    purchase_mail_attachment_vendor_docs = fields.Boolean(
        related='company_id.purchase_mail_attach_vendor_docs',
        readonly=False,
        string='Include Vendor Documents',
    )
    purchase_mail_attachment_max_count = fields.Integer(
        related='company_id.purchase_mail_attach_max_count',
        readonly=False,
        string='Max Attachment Count',
    )
    purchase_mail_attachment_max_mb = fields.Float(
        related='company_id.purchase_mail_attach_max_mb',
        readonly=False,
        string='Max Total Attachment Size (MB)',
    )
