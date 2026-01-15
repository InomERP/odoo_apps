from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    code = fields.Char(string='Code')