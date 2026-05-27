from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEBilling(models.Model):

    _name = 'oeh.billing'
    _description = 'Billing Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(default='New', readonly=True, tracking=True)

    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    doctor_id = fields.Many2one('oeh.doctor')

    bill_date = fields.Date(default=fields.Date.context_today)

    total_amount = fields.Float(required=True)

    invoice_id = fields.Many2one('account.move', string='Invoice')

    # -------------------------
    # REAL PAID AMOUNT (FIXED)
    # -------------------------
    paid_amount = fields.Float(
        compute='_compute_paid_amount',
        store=True
    )

    balance = fields.Float(
        compute='_compute_balance',
        store=True
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('partial', 'Partial'),
        ('paid', 'Paid')
    ], compute='_compute_status', store=True, tracking=True)

    # -------------------------
    # INVOICE LIFECYCLE (workflow stage, separate from payment status)
    # -------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
        ('refund', 'Refunded'),
    ], string='Stage', default='draft', tracking=True, copy=False)

    # -------------------------
    # TAX / INSURANCE DEDUCTION
    # -------------------------
    tax_amount = fields.Float(string='Tax', tracking=True)
    insurance_claim_id = fields.Many2one(
        'oeh.insurance.claim', string='Insurance Claim', tracking=True)
    insurance_coverage = fields.Float(string='Insurance Coverage', tracking=True)
    patient_payable = fields.Float(
        string='Patient Payable', compute='_compute_patient_payable', store=True)

    # -------------------------
    # PAYMENT HISTORY / SMART BUTTON
    # -------------------------
    payment_ids = fields.One2many('oeh.payment', 'billing_id', string='Payments')
    payment_count = fields.Integer(compute='_compute_payment_count')

    @api.depends('total_amount', 'tax_amount', 'insurance_coverage')
    def _compute_patient_payable(self):
        for rec in self:
            rec.patient_payable = (
                (rec.total_amount or 0.0)
                + (rec.tax_amount or 0.0)
                - (rec.insurance_coverage or 0.0)
            )

    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    @api.constrains('total_amount', 'tax_amount', 'insurance_coverage')
    def _check_billing_amounts(self):
        for rec in self:
            if rec.total_amount < 0:
                raise ValidationError(_("Total amount cannot be negative."))
            if rec.tax_amount < 0:
                raise ValidationError(_("Tax cannot be negative."))
            if rec.insurance_coverage < 0:
                raise ValidationError(_("Insurance coverage cannot be negative."))
            if rec.insurance_coverage > (rec.total_amount + rec.tax_amount):
                raise ValidationError(_(
                    "Insurance coverage cannot exceed billed amount + tax."))


    # -------------------------
    # SEQUENCE
    # -------------------------
    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.billing') or 'New'

        return super().create(vals_list)


    # -------------------------
    # PAID AMOUNT (REAL ODOO WAY)
    # -------------------------
    @api.depends('invoice_id.amount_total', 'invoice_id.amount_residual')
    def _compute_paid_amount(self):

        for rec in self:

            if not rec.invoice_id:
                rec.paid_amount = 0.0
            else:
                rec.paid_amount = rec.invoice_id.amount_total - rec.invoice_id.amount_residual


    # -------------------------
    # BALANCE
    # -------------------------
    @api.depends('total_amount', 'paid_amount')
    def _compute_balance(self):

        for rec in self:
            rec.balance = rec.total_amount - rec.paid_amount


    # -------------------------
    # STATUS
    # -------------------------
    @api.depends('invoice_id.payment_state')
    def _compute_status(self):

        for rec in self:

            if not rec.invoice_id:
                rec.status = 'draft'

            elif rec.invoice_id.payment_state == 'paid':
                rec.status = 'paid'

            elif rec.invoice_id.payment_state in ['partial', 'in_payment']:
                rec.status = 'partial'

            else:
                rec.status = 'draft'


    # -------------------------
    # CREATE INVOICE
    # -------------------------
    def action_create_invoice(self):

        for rec in self:

            if rec.invoice_id:
                continue

            partner = rec.patient_id.partner_id

            invoice = self.env['account.move'].create({

                'move_type': 'out_invoice',
                'partner_id': partner.id if partner else False,
                'invoice_date': rec.bill_date,

                'invoice_line_ids': [(0, 0, {
                    'name': 'Hospital Billing',
                    'quantity': 1,
                    'price_unit': rec.total_amount,
                })]

            })

            rec.invoice_id = invoice.id


    # -------------------------
    # OPEN INVOICE
    # -------------------------
    def action_open_invoice(self):

        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------
    # WORKFLOW TRANSITIONS
    # -------------------------
    def action_confirm(self):
        for rec in self:
            if rec.total_amount <= 0:
                raise ValidationError(_(
                    "Cannot confirm a bill with a zero total amount."))
            rec.state = 'confirmed'

    def action_post_bill(self):
        """Create + post the customer invoice, then mark the bill Posted."""
        for rec in self:
            if not rec.invoice_id:
                rec.action_create_invoice()
            if rec.invoice_id and rec.invoice_id.state == 'draft':
                rec.invoice_id.action_post()
            rec.state = 'posted'

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_refund(self):
        """Create a credit note (reversal) for the posted invoice."""
        for rec in self:
            if rec.invoice_id and rec.invoice_id.state == 'posted':
                rec.invoice_id._reverse_moves([{
                    'invoice_date': fields.Date.context_today(rec),
                }])
            rec.state = 'refund'

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments'),
            'res_model': 'oeh.payment',
            'view_mode': 'list,form',
            'domain': [('billing_id', '=', self.id)],
            'context': {'default_billing_id': self.id},
        }