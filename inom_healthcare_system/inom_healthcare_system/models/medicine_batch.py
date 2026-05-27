from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEMedicineBatch(models.Model):

    _name = 'oeh.medicine.batch'
    _description = 'Medicine Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'batch_no'
    _order = 'expiry_date asc'

    # ---- Existing fields (preserved) ----
    batch_no = fields.Char(required=True, tracking=True)

    medicine_id = fields.Many2one(
        'oeh.pharmacy',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    quantity = fields.Integer()

    expiry_date = fields.Date(tracking=True)

    status = fields.Selection([
        ('available', 'Available'),
        ('expired', 'Expired'),
        ('finished', 'Finished')
    ], default='available', tracking=True)

    # ---- Professional additions ----
    mfg_date = fields.Date(string='Manufacturing Date')
    is_expired = fields.Boolean(compute='_compute_expiry', store=True)
    days_to_expiry = fields.Integer(compute='_compute_expiry')
    expiry_status = fields.Selection([
        ('none', 'No Expiry Set'),
        ('expired', 'Expired'),
        ('near', 'Near Expiry'),
        ('ok', 'OK'),
    ], compute='_compute_expiry', store=True, string='Expiry Status')

    @api.depends('expiry_date', 'status')
    def _compute_expiry(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.expiry_date:
                rec.is_expired = False
                rec.days_to_expiry = 0
                rec.expiry_status = 'none'
                continue
            delta = (rec.expiry_date - today).days
            rec.days_to_expiry = delta
            rec.is_expired = delta < 0
            if delta < 0:
                rec.expiry_status = 'expired'
            elif delta <= 90:
                rec.expiry_status = 'near'
            else:
                rec.expiry_status = 'ok'

    # ---- Validations ----
    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError(_("Batch quantity cannot be negative."))

    @api.constrains('mfg_date', 'expiry_date')
    def _check_dates(self):
        for rec in self:
            if rec.mfg_date and rec.expiry_date and rec.expiry_date < rec.mfg_date:
                raise ValidationError(_(
                    "Expiry date cannot be earlier than the manufacturing date."))

    # ---- Existing method (preserved) ----
    @api.model
    def update_stock_from_batch(self):
        for rec in self:
            rec.medicine_id.stock_qty += rec.quantity

    # ---- Workflow ----
    def action_mark_expired(self):
        self.write({'status': 'expired'})

    def action_mark_finished(self):
        self.write({'status': 'finished'})

    def action_add_to_stock(self):
        """Add this batch quantity to the medicine stock (FEFO/FIFO intake)."""
        for rec in self:
            if rec.is_expired:
                raise ValidationError(_(
                    "Cannot add an expired batch (%s) to stock.") % rec.batch_no)
            rec.medicine_id.stock_qty += rec.quantity
