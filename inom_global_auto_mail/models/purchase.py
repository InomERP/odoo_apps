from odoo import models, fields

class PurchaseOrder(models.Model):
	_inherit = "purchase.order"

	auto_mail_sent = fields.Boolean(string="Auto Mail Sent", default=False)