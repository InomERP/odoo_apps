from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HealthcarePosService(models.Model):
    """A sellable healthcare item displayed in the POS product grid.

    A service can be a flat clinical item (a consultation, a lab test, a
    radiology scan, a treatment/procedure) or it can be linked to a pharmacy
    medicine (``inom.pharmacy``) so that selling it decrements real stock and
    pulls the live sale price.
    """

    _name = 'healthcare.pos.service'
    _description = 'Healthcare POS Service'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string='Reference', copy=False, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    category_id = fields.Many2one(
        'healthcare.pos.category', string='Category',
        required=True, ondelete='restrict')

    service_type = fields.Selection([
        ('consultation', 'Consultation'),
        ('lab', 'Laboratory Test'),
        ('radiology', 'Radiology / Imaging'),
        ('pharmacy', 'Pharmacy / Medicine'),
        ('treatment', 'Treatment'),
        ('procedure', 'Procedure'),
        ('other', 'Other'),
    ], default='other', required=True,
        help="Drives the clinical record created when the order is paid.")

    list_price = fields.Float(string='Sales Price', digits='Product Price')
    tax_percent = fields.Float(string='Tax %', default=0.0)

    # Optional link to a pharmacy medicine. When set, price and stock follow it.
    pharmacy_id = fields.Many2one('inom.pharmacy', string='Linked Medicine')
    track_stock = fields.Boolean(
        string='Track Stock', help="Decrement linked medicine stock when sold.")

    image_1920 = fields.Image()
    color = fields.Char(help="Optional card accent colour.")

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)

    available_in_pos = fields.Boolean(string='Available in POS', default=True)

    @api.onchange('pharmacy_id')
    def _onchange_pharmacy_id(self):
        if self.pharmacy_id:
            self.service_type = 'pharmacy'
            self.track_stock = True
            if not self.name:
                self.name = self.pharmacy_id.name
            if not self.list_price:
                self.list_price = self.pharmacy_id.price

    @api.constrains('list_price', 'tax_percent')
    def _check_amounts(self):
        for rec in self:
            if rec.list_price < 0:
                raise ValidationError(_("Sales price cannot be negative."))
            if rec.tax_percent < 0 or rec.tax_percent > 100:
                raise ValidationError(_("Tax %% must be between 0 and 100."))

    def _get_live_price(self):
        """Return the price to charge, preferring the linked medicine price."""
        self.ensure_one()
        if self.pharmacy_id:
            return self.pharmacy_id.price or self.list_price
        return self.list_price
