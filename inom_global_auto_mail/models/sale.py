from odoo import models, fields

class SaleOrder(models.Model):
	_inherit = "sale.order"

	auto_mail_sent = fields.Boolean(string="Auto Mail Sent", default=False)