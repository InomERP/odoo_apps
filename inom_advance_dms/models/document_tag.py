from odoo import models, fields


class EdmTag(models.Model):
    _name = 'edm.tag'
    _description = 'Document Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color')