from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    email_cc_enable = fields.Boolean(
        string="Enable Default CC",
        config_parameter="inom_mail_cc_bcc.email_cc_enable",
    )
    email_bcc_enable = fields.Boolean(
        string="Enable Default BCC",
        config_parameter="inom_mail_cc_bcc.email_bcc_enable",
    )
    reply_to_enable = fields.Boolean(
        string="Enable Default Reply-To",
        config_parameter="inom_mail_cc_bcc.reply_to_enable",
    )
    email_cc_text = fields.Char(
        string="Email CC",
        config_parameter="inom_mail_cc_bcc.email_cc_text",
    )
    email_bcc_text = fields.Char(
        string="Email BCC",
        config_parameter="inom_mail_cc_bcc.email_bcc_text",
    )
    reply_to_text = fields.Char(
        string="Reply-To Email",
        config_parameter="inom_mail_cc_bcc.reply_to_text",
    )
