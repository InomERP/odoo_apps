from odoo import models, fields

class AccountMove(models.Model):
	_inherit = 'account.move'

	auto_mail_sent = fields.Boolean(string="Auto Mail Sent", default=False)