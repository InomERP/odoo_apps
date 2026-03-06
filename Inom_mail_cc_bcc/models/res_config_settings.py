from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    email_cc_enable = fields.Boolean(
        string="Enable Default CC",
        default_model='ir.config_parameter'
    )
    email_bcc_enable = fields.Boolean(
        string="Enable Default BCC",
        default_model='ir.config_parameter'
    )
    reply_to_enable = fields.Boolean(
        string="Enable Default Reply-To",
        default_model='ir.config_parameter'
    )
    email_cc_text = fields.Text(
        string="Email CC",
        default_model='ir.config_parameter'
    )
    email_bcc_text = fields.Text(
        string="Email BCC",
        default_model='ir.config_parameter'
    )
    reply_to_text = fields.Text(
        string="Reply-To Email",
        default_model='ir.config_parameter'
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update({
            'email_cc_enable': ICP.get_param('Inom_mail_cc_bcc.email_cc_enable', default='False') == 'True',
            'email_bcc_enable': ICP.get_param('Inom_mail_cc_bcc.email_bcc_enable', default='False') == 'True',
            'reply_to_enable': ICP.get_param('Inom_mail_cc_bcc.reply_to_enable', default='False') == 'True',
            'email_cc_text': ICP.get_param('Inom_mail_cc_bcc.email_cc_text', default=''),
            'email_bcc_text': ICP.get_param('Inom_mail_cc_bcc.email_bcc_text', default=''),
            'reply_to_text': ICP.get_param('Inom_mail_cc_bcc.reply_to_text', default=''),
        })
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('Inom_mail_cc_bcc.email_cc_enable', str(self.email_cc_enable))
        ICP.set_param('Inom_mail_cc_bcc.email_bcc_enable', str(self.email_bcc_enable))
        ICP.set_param('Inom_mail_cc_bcc.reply_to_enable', str(self.reply_to_enable))
        ICP.set_param('Inom_mail_cc_bcc.email_cc_text', self.email_cc_text if self.email_cc_enable else '')
        ICP.set_param('Inom_mail_cc_bcc.email_bcc_text', self.email_bcc_text if self.email_bcc_enable else '')
        ICP.set_param('Inom_mail_cc_bcc.reply_to_text', self.reply_to_text if self.reply_to_enable else '')