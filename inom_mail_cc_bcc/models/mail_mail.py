from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    # CC/BCC/Reply-To are injected by mail.compose.message._prepare_mail_values()
    # in Odoo 20. No send() override is required.
