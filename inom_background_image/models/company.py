from odoo import models, fields 

class ResCompany(models.Model):
	_inherit = "res.company"

	login_background = fields.Binary("Login Background Image")