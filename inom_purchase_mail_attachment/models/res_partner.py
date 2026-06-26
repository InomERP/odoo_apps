# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    purchase_mail_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='res_partner_purchase_mail_attachment_rel',
        column1='partner_id',
        column2='attachment_id',
        string='Purchase Email Documents',
        help="Documents stored on this vendor that are automatically attached "
             "to Request for Quotation / Purchase Order emails sent to the "
             "vendor (e.g. NDA, quality terms, vendor onboarding pack).",
    )
    disable_purchase_mail_attachment = fields.Boolean(
        string='Skip Auto Attachments',
        help="If enabled, product and vendor documents are never auto-attached "
             "to purchase emails sent to this vendor.",
    )
