from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    email_cc = fields.Char("CC")
    email_bcc = fields.Char("BCC")

    show_bcc = fields.Boolean("Add BCC")  

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        ICP = self.env['ir.config_parameter'].sudo()

        cc_enabled = ICP.get_param('Inom_mail_cc_bcc.email_cc_enable') == 'True'
        bcc_enabled = ICP.get_param('Inom_mail_cc_bcc.email_bcc_enable') == 'True'

        if cc_enabled:
            res['email_cc'] = ICP.get_param('Inom_mail_cc_bcc.email_cc_text')

        if bcc_enabled:
            res['email_bcc'] = ICP.get_param('Inom_mail_cc_bcc.email_bcc_text')

        return res

    def _validate_emails(self, emails):
        if emails:
            for email in emails.split(','):
                email = email.strip()
                if email and not re.match(EMAIL_REGEX, email):
                    raise ValidationError("Invalid email: %s" % email)

    def get_mail_values(self, res_ids):

        mail_values = super().get_mail_values(res_ids)

        for res_id in res_ids:
            if res_id in mail_values:

                values = mail_values[res_id]

                if self.email_cc:
                    values['email_cc'] = self.email_cc

                if self.email_bcc:
                    values['email_bcc'] = self.email_bcc

                mail_values[res_id] = values

        return mail_values

    def action_send_mail(self):

        self._validate_emails(self.email_cc)
        self._validate_emails(self.email_bcc)

        res = super().action_send_mail()

        mails = self.env['mail.mail'].search([
            ('mail_message_id', '!=', False)
        ], order='id desc', limit=10)

        for mail in mails:
            if self.email_cc:
                mail.email_cc = self.email_cc

            if self.email_bcc:
                mail.email_bcc = self.email_bcc

        return res