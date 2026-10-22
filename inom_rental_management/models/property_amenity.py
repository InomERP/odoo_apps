from odoo import fields, models


class PropertyAmenity(models.Model):
    _name = 'property.amenity'
    _description = 'Property Amenity'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        'UNIQUE(name)',
        'An amenity with this name already exists.',
    )
