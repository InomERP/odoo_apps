from odoo import models, fields


class MailMessage(models.Model):
    _inherit = 'mail.message'

    email_cc = fields.Char(string="CC")
    email_bcc = fields.Char(string="BCC")