from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEPrescriptionDispense(models.Model):

    _name = 'oeh.prescription.dispense'
    _description = 'Prescription Dispense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'medicine_id'
    _order = 'date desc, id desc'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    doctor_id = fields.Many2one('oeh.doctor', tracking=True)

    medicine_id = fields.Many2one('oeh.pharmacy', required=True, tracking=True)

    quantity = fields.Integer(required=True)

    date = fields.Datetime(default=fields.Datetime.now)

    # Original keys (draft/issued/done) kept; professional stages appended.
    state = fields.Selection([
        ('draft', 'Pending'),
        ('verified', 'Verified'),
        ('issued', 'Issued'),
        ('done', 'Dispensed'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    # ---- Professional additions ----
    name = fields.Char(string='Dispense Ref', default='New', readonly=True,
                       copy=False, index=True)
    pharmacist_id = fields.Many2one('res.users', string='Verified By',
                                    readonly=True, copy=False)
    prescription_id = fields.Many2one('oeh.prescription', string='Prescription')
    unit_price = fields.Float(related='medicine_id.price', readonly=True)
    total_price = fields.Float(compute='_compute_total_price', store=True)
    billing_id = fields.Many2one('oeh.billing', string='Bill', copy=False)
    stock_moved = fields.Boolean(default=False, copy=False, readonly=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = (rec.quantity or 0) * (rec.unit_price or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'oeh.prescription.dispense') or 'New'
        return super().create(vals_list)

    @api.depends('name', 'medicine_id', 'patient_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'New':
                rec.display_name = '%s - %s' % (rec.name, rec.medicine_id.name or '')
            else:
                rec.display_name = rec.medicine_id.display_name or _('Dispense')

    # ---- Validations ----
    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("Dispense quantity must be greater than zero."))

    def _check_dispensable(self):
        """Block dispensing of expired medicine or insufficient stock."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        med = self.medicine_id
        if med.expiry_date and med.expiry_date < today:
            raise ValidationError(_(
                "Medicine '%s' has expired (expiry %s) and cannot be dispensed.")
                % (med.name, med.expiry_date))
        # If batches exist, require at least one available, non-expired batch.
        if med.batch_ids:
            usable = med.batch_ids.filtered(
                lambda b: b.status == 'available' and not b.is_expired)
            if not usable:
                raise ValidationError(_(
                    "No available (non-expired) batch for medicine '%s'.") % med.name)
        if med.stock_qty < self.quantity:
            raise ValidationError(_(
                "Not enough stock for '%s' (available: %s, requested: %s).")
                % (med.name, med.stock_qty, self.quantity))

    def _move_stock(self):
        """Decrement medicine stock exactly once."""
        for rec in self:
            if not rec.stock_moved:
                rec.medicine_id.stock_qty -= rec.quantity
                rec.stock_moved = True

    # ---- Workflow transitions ----
    def action_verify(self):
        for rec in self:
            rec._check_dispensable()
            rec.write({'state': 'verified', 'pharmacist_id': self.env.user.id})

    def action_dispense(self):
        for rec in self:
            rec._check_dispensable()
            rec._move_stock()
            rec.state = 'done'

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset(self):
        self.write({'state': 'draft'})

    # ---- Existing method (preserved, hardened against double stock move) ----
    def action_issue(self):
        for rec in self:
            rec._check_dispensable()
            rec._move_stock()
            rec.state = 'issued'

    # ---- Billing integration (creates a finance bill; finance code untouched) ----
    def action_create_billing(self):
        self.ensure_one()
        if not self.billing_id:
            self.billing_id = self.env['oeh.billing'].create({
                'patient_id': self.patient_id.id,
                'doctor_id': self.doctor_id.id if self.doctor_id else False,
                'total_amount': self.total_price,
            }).id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bill'),
            'res_model': 'oeh.billing',
            'res_id': self.billing_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
