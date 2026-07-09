# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    inom_whatsapp_enabled = fields.Boolean(
        string='Enable WhatsApp Notifications')
    inom_whatsapp_country_code = fields.Char(
        string='Default Country Code', default='+91',
        help='Prepended to mobile numbers that are stored without a '
             'country code.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inom_whatsapp_enabled = fields.Boolean(
        related='company_id.inom_whatsapp_enabled', readonly=False,
        string='Enable WhatsApp Notifications')
    inom_whatsapp_country_code = fields.Char(
        related='company_id.inom_whatsapp_country_code', readonly=False,
        string='Default Country Code')
