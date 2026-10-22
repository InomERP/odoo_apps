from odoo import fields, models


class PropertyImage(models.Model):
    _name = 'property.image'
    _description = 'Property Image'
    _inherit = ['image.mixin']
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    image_1920 = fields.Image(required=True)
    property_id = fields.Many2one('property.property', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='property_id.company_id', store=True, index=True)
