from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEPharmacy(models.Model):

    _name = 'oeh.pharmacy'
    _description = 'Pharmacy Medicine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ---- Existing fields (preserved) ----
    name = fields.Char(required=True, tracking=True)

    medicine_type = fields.Selection([
        ('tablet', 'Tablet'),
        ('syrup', 'Syrup'),
        ('capsule', 'Capsule'),
        ('injection', 'Injection')
    ], default='tablet')

    price = fields.Float()

    stock_qty = fields.Integer(default=0, tracking=True)

    min_stock = fields.Integer(default=5)

    expiry_date = fields.Date()

    batch_ids = fields.One2many('oeh.medicine.batch', 'medicine_id')

    is_low_stock = fields.Boolean(compute='_compute_low_stock', store=True)

    @api.depends('stock_qty', 'min_stock')
    def _compute_low_stock(self):
        for rec in self:
            rec.is_low_stock = rec.stock_qty <= rec.min_stock

    # ---- Professional additions: Medicine Management ----
    code = fields.Char(string='Medicine Code', default='New', readonly=True, copy=False, index=True)
    active = fields.Boolean(default=True)
    generic_name = fields.Char(string='Generic Name')
    brand_name = fields.Char(string='Brand Name')
    is_generic = fields.Boolean(string='Generic')
    strength = fields.Char(string='Strength', help="e.g. 500 mg")
    dosage_info = fields.Char(string='Dosage Information')
    drug_category = fields.Selection([
        ('antibiotic', 'Antibiotic'),
        ('analgesic', 'Analgesic'),
        ('antipyretic', 'Antipyretic'),
        ('antacid', 'Antacid'),
        ('antiseptic', 'Antiseptic'),
        ('vaccine', 'Vaccine'),
        ('supplement', 'Supplement'),
        ('other', 'Other'),
    ], default='other')
    manufacturer_id = fields.Many2one('res.partner', string='Manufacturer')
    storage_instructions = fields.Text()
    is_controlled = fields.Boolean(string='Controlled Medicine',
                                   help="Requires special handling / regulatory control")

    # ---- Inventory & stock logic ----
    reserved_qty = fields.Integer(default=0, string='Reserved Qty')
    available_qty = fields.Integer(compute='_compute_available_qty', store=True,
                                   string='Available Qty')
    nearest_expiry = fields.Date(compute='_compute_batch_stats', store=True,
                                 string='Nearest Expiry (FEFO)')
    batch_count = fields.Integer(compute='_compute_batch_stats')
    dispense_count = fields.Integer(compute='_compute_dispense_count')

    @api.depends('stock_qty', 'reserved_qty')
    def _compute_available_qty(self):
        for rec in self:
            rec.available_qty = (rec.stock_qty or 0) - (rec.reserved_qty or 0)

    @api.depends('batch_ids', 'batch_ids.expiry_date', 'batch_ids.status')
    def _compute_batch_stats(self):
        for rec in self:
            rec.batch_count = len(rec.batch_ids)
            valid = rec.batch_ids.filtered(
                lambda b: b.expiry_date and b.status == 'available')
            rec.nearest_expiry = min(valid.mapped('expiry_date')) if valid else False

    def _compute_dispense_count(self):
        Dispense = self.env['oeh.prescription.dispense']
        for rec in self:
            rec.dispense_count = Dispense.search_count([('medicine_id', '=', rec.id)])

    # ---- Validations ----
    @api.constrains('stock_qty', 'price', 'min_stock', 'reserved_qty')
    def _check_pharmacy_numbers(self):
        for rec in self:
            if rec.stock_qty < 0:
                raise ValidationError(_("Stock quantity cannot be negative."))
            if rec.price < 0:
                raise ValidationError(_("Price cannot be negative."))
            if rec.min_stock < 0:
                raise ValidationError(_("Minimum stock cannot be negative."))
            if rec.reserved_qty < 0:
                raise ValidationError(_("Reserved quantity cannot be negative."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') in (False, 'New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('oeh.pharmacy') or 'New'
        return super().create(vals_list)

    # ---- Smart buttons ----
    def action_view_batches(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Batches'),
            'res_model': 'oeh.medicine.batch',
            'view_mode': 'list,form',
            'domain': [('medicine_id', '=', self.id)],
            'context': {'default_medicine_id': self.id},
        }

    def action_view_dispenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dispenses'),
            'res_model': 'oeh.prescription.dispense',
            'view_mode': 'list,form',
            'domain': [('medicine_id', '=', self.id)],
            'context': {'default_medicine_id': self.id},
        }
