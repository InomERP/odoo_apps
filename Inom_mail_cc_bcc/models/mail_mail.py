from odoo import models

class MailMail(models.Model):
    _inherit = 'mail.mail'

    def send(self, auto_commit=False, raise_exception=False):
        for mail in self:

            if mail.mail_message_id:

                message = mail.mail_message_id

                if message.email_cc:
                    mail.email_cc = message.email_cc

                if message.email_bcc:
                    mail.email_bcc = message.email_bcc

        return super().send(
            auto_commit=auto_commit,
            raise_exception=raise_exception
        )