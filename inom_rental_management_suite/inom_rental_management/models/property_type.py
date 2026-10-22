from odoo import fields, models


class PropertyType(models.Model):
    _name = 'property.type'
    _description = 'Property Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        selection=[
            ('land', 'Land'),
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
            ('industrial', 'Industrial'),
        ],
        required=True,
        default='residential',
    )
    active = fields.Boolean(default=True)

    _name_category_uniq = models.Constraint(
        'UNIQUE(name, category)',
        'A property type with this name already exists in this category.',
    )
