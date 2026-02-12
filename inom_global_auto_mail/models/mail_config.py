from odoo import models, fields, api
from datetime import timedelta


class GlobalMailConfig(models.Model):
    _name = 'global.mail.config'
    _description = 'Global Auto Mail Configuration'

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade'
    )
    days_after = fields.Integer(
        string='Send After (Days)',
        default=0
    )
    template_id = fields.Many2one(
        'mail.template',
        string='Mail Template',
        required=True
    )
    active = fields.Boolean(default=True)

    def _send_auto_mails(self):
        today = fields.Date.today()

        for config in self.search([('active', '=', True)]):
            Model = self.env[config.model_id.model]

            target_date = today - timedelta(days=config.days_after)

            domain = [
                ('create_date', '<=', target_date),
                ('auto_mail_sent', '=', False)
            ]

            records = Model.search(domain)

            for rec in records:
                try:
                    config.template_id.send_mail(
                        rec.id,
                        force_send=True
                    )
                    rec.auto_mail_sent = True
                except Exception:
                    continue
