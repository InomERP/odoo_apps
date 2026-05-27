from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEPayment(models.Model):

    _name = 'oeh.payment'
    _description = 'Payments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'payment_date desc, id desc'

    # ---- Existing fields (preserved) ----
    billing_id = fields.Many2one(
        'oeh.billing',
        required=True
    )

    payment_date = fields.Date(required=True, default=fields.Date.context_today)

    amount = fields.Float(required=True)

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('bank', 'Bank')
    ], required=True)

    reference = fields.Char()

    # ---- Professional additions ----
    name = fields.Char(
        string='Receipt No', default='New', readonly=True, copy=False,
        index=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True, copy=False)

    payment_kind = fields.Selection([
        ('regular', 'Regular'),
        ('advance', 'Advance'),
        ('refund', 'Refund'),
    ], string='Type', default='regular', tracking=True)

    patient_id = fields.Many2one(
        'oeh.patient', related='billing_id.patient_id',
        store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'oeh.payment') or 'New'
        return super().create(vals_list)

    @api.depends('name', 'amount', 'billing_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'New':
                rec.display_name = '%s (%s)' % (rec.name, rec.amount)
            elif rec.billing_id:
                rec.display_name = rec.billing_id.display_name
            else:
                rec.display_name = _('New Payment')

    @api.constrains('amount')
    def _check_amount_positive(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Payment amount must be greater than zero."))

    # ---- Workflow ----
    def action_post(self):
        self.write({'state': 'posted'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset(self):
        self.write({'state': 'draft'})
