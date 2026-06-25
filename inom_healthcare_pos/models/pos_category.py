from odoo import models, fields, api


class HealthcarePosCategory(models.Model):
    """Groups the sellable healthcare items shown as tabs in the POS grid
    (e.g. Consultation, Laboratory, Radiology, Pharmacy, Treatment)."""

    _name = 'healthcare.pos.category'
    _description = 'Healthcare POS Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    # FontAwesome icon name (without the leading "fa-") used in the POS UI.
    icon = fields.Char(default='stethoscope', help="FontAwesome icon name without the 'fa-' prefix.")
    color = fields.Char(default='#0d9488', help="Accent colour used for the category tab/card.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    service_ids = fields.One2many('healthcare.pos.service', 'category_id', string='Services')
    service_count = fields.Integer(compute='_compute_service_count')

    def _compute_service_count(self):
        data = self.env['healthcare.pos.service']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count'])
        mapped = {cat.id: count for cat, count in data}
        for rec in self:
            rec.service_count = mapped.get(rec.id, 0)
