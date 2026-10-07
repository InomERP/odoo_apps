from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    login_background = fields.Binary("Login Background Image")
