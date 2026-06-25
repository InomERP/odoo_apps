from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HealthcarePosOrder(models.Model):
    """A POS transaction for a patient. Created/settled from the OWL UI and,
    on payment, propagated into the healthcare backend: a hospital bill, the
    matching clinical records (lab / radiology / treatment) and pharmacy stock
    moves are generated so the till stays in sync with patient records."""

    _name = 'healthcare.pos.order'
    _description = 'Healthcare POS Order'
    _order = 'date_order desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(default='/', readonly=True, copy=False, index=True)
    session_id = fields.Many2one(
        'healthcare.pos.session', string='Session',
        required=True, ondelete='restrict', index=True)
    config_id = fields.Many2one(
        'healthcare.pos.config', related='session_id.config_id',
        store=True, readonly=True)
    company_id = fields.Many2one(
        'res.company', related='session_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='session_id.currency_id', store=True, readonly=True)
    user_id = fields.Many2one(
        'res.users', string='Cashier', default=lambda self: self.env.user)

    patient_id = fields.Many2one('inom.patient', string='Patient', tracking=True)
    doctor_id = fields.Many2one('inom.doctor', string='Doctor')
    date_order = fields.Datetime(string='Order Date', default=fields.Datetime.now)
    note = fields.Text()

    line_ids = fields.One2many('healthcare.pos.order.line', 'order_id', string='Lines')
    payment_ids = fields.One2many('healthcare.pos.payment', 'order_id', string='Payments')

    amount_untaxed = fields.Float(compute='_compute_amounts', store=True)
    amount_tax = fields.Float(compute='_compute_amounts', store=True)
    amount_total = fields.Float(compute='_compute_amounts', store=True)
    amount_paid = fields.Float(compute='_compute_paid', store=True)
    amount_due = fields.Float(compute='_compute_paid', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('done', 'Done'),
        ('invoiced', 'Invoiced'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True, copy=False)

    billing_id = fields.Many2one('inom.billing', string='Hospital Bill', copy=False)

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_total')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_untaxed = sum(rec.line_ids.mapped('price_subtotal'))
            rec.amount_tax = sum(rec.line_ids.mapped('price_tax'))
            rec.amount_total = sum(rec.line_ids.mapped('price_total'))

    @api.depends('payment_ids.amount', 'amount_total')
    def _compute_paid(self):
        for rec in self:
            rec.amount_paid = sum(rec.payment_ids.mapped('amount'))
            rec.amount_due = rec.amount_total - rec.amount_paid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') in ('/', False):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'healthcare.pos.order') or '/'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # UI serialisation helpers
    # ------------------------------------------------------------------
    @api.model
    def _patient_ui_data(self, patient):
        return {
            'id': patient.id,
            'name': patient.name,
            'ref': patient.patient_id or '',
            'phone': patient.phone or '',
            'email': patient.email or '',
            'gender': patient.gender or '',
            'blood_group': patient.blood_group or '',
            'age': patient.age or 0,
        }

    @api.model
    def create_patient_from_ui(self, vals):
        """Create a patient (and its res.partner) straight from the POS popup."""
        Patient = self.env['inom.patient'].sudo()
        clean = {
            'name': vals.get('name'),
            'phone': vals.get('phone') or False,
            'email': vals.get('email') or False,
            'gender': vals.get('gender') or False,
            'blood_group': vals.get('blood_group') or False,
            'age': int(vals['age']) if vals.get('age') else 0,
            'address': vals.get('address') or False,
        }
        if not clean['name']:
            raise UserError(_("A patient name is required."))
        # Mirror to a contact so downstream invoicing works.
        partner = self.env['res.partner'].sudo().create({
            'name': clean['name'],
            'phone': clean['phone'],
            'email': clean['email'],
        })
        clean['partner_id'] = partner.id
        patient = Patient.create(clean)
        return self._patient_ui_data(patient)

    # ------------------------------------------------------------------
    # Order settlement from the OWL UI
    # ------------------------------------------------------------------
    @api.model
    def settle_order_from_ui(self, payload):
        """Persist a completed order coming from the POS screen.

        ``payload`` = {
            session_id, patient_id, doctor_id, note,
            lines: [{service_id, qty, price_unit, tax_percent, discount}],
            payments: [{payment_method_id, amount, is_cash}],
        }
        Returns the receipt data.
        """
        session = self.env['healthcare.pos.session'].browse(payload['session_id']).exists()
        if not session or session.state not in ('opened', 'opening_control'):
            raise UserError(_("The POS session is not open."))
        if session.state == 'opening_control':
            session.action_open_session()

        config = session.config_id
        if config.require_patient and not payload.get('patient_id'):
            raise UserError(_("This Point of Sale requires a patient on every order."))

        order = self.create({
            'session_id': session.id,
            'patient_id': payload.get('patient_id') or False,
            'doctor_id': payload.get('doctor_id') or False,
            'note': payload.get('note') or False,
            'date_order': fields.Datetime.now(),
        })

        for line in payload.get('lines', []):
            self.env['healthcare.pos.order.line'].create({
                'order_id': order.id,
                'service_id': line['service_id'],
                'qty': line.get('qty', 1.0),
                'price_unit': line.get('price_unit', 0.0),
                'tax_percent': line.get('tax_percent', 0.0),
                'discount': line.get('discount', 0.0),
            })

        for pay in payload.get('payments', []):
            self.env['healthcare.pos.payment'].create({
                'order_id': order.id,
                'payment_method_id': pay['payment_method_id'],
                'amount': pay['amount'],
            })

        order._on_order_paid()
        return order._receipt_data()

    def _on_order_paid(self):
        self.ensure_one()
        self.state = 'paid'
        if self.config_id.generate_billing and self.patient_id:
            self._create_hospital_bill()
        if self.config_id.generate_clinical_records and self.patient_id:
            self._create_clinical_records()
        self._apply_stock_moves()
        self.state = 'done'

    def _create_hospital_bill(self):
        self.ensure_one()
        if self.billing_id:
            return
        self.billing_id = self.env['inom.billing'].sudo().create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id if self.doctor_id else False,
            'total_amount': self.amount_untaxed,
            'tax_amount': self.amount_tax,
        }).id

    def _create_clinical_records(self):
        """Spin up the relevant backend clinical record per service line so
        the order is visible from the patient's lab/radiology/treatment lists."""
        self.ensure_one()
        for line in self.line_ids:
            stype = line.service_id.service_type
            if stype == 'lab':
                self.env['inom.laboratory'].sudo().create({
                    'patient_id': self.patient_id.id,
                    'test_name': line.service_id.name,
                })
            elif stype == 'radiology':
                self.env['inom.radiology'].sudo().create({
                    'patient_id': self.patient_id.id,
                    'scan_type': line.service_id.name,
                })
            elif stype == 'treatment':
                self.env['inom.treatment'].sudo().create({
                    'patient_id': self.patient_id.id,
                    'doctor_id': self.doctor_id.id if self.doctor_id else False,
                    'treatment_name': line.service_id.name,
                    'fee': line.price_subtotal,
                })

    def _apply_stock_moves(self):
        self.ensure_one()
        for line in self.line_ids:
            service = line.service_id
            if service.track_stock and service.pharmacy_id:
                medicine = service.pharmacy_id.sudo()
                medicine.stock_qty = max(0, (medicine.stock_qty or 0) - int(line.qty))

    def _receipt_data(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'date_order': fields.Datetime.to_string(self.date_order),
            'patient': self.patient_id.name or _('Walk-in'),
            'patient_ref': self.patient_id.patient_id or '',
            'doctor': self.doctor_id.name or '',
            'cashier': self.user_id.name,
            'lines': [{
                'name': l.service_id.name,
                'qty': l.qty,
                'price_unit': l.price_unit,
                'discount': l.discount,
                'subtotal': l.price_subtotal,
                'total': l.price_total,
            } for l in self.line_ids],
            'amount_untaxed': self.amount_untaxed,
            'amount_tax': self.amount_tax,
            'amount_total': self.amount_total,
            'payments': [{
                'method': p.payment_method_id.name,
                'amount': p.amount,
            } for p in self.payment_ids],
            'bill_ref': self.billing_id.name if self.billing_id else '',
        }

    def action_cancel(self):
        self.write({'state': 'cancel'})


class HealthcarePosOrderLine(models.Model):
    _name = 'healthcare.pos.order.line'
    _description = 'Healthcare POS Order Line'

    order_id = fields.Many2one(
        'healthcare.pos.order', required=True, ondelete='cascade', index=True)
    service_id = fields.Many2one(
        'healthcare.pos.service', string='Service', required=True)
    name = fields.Char(string='Description')
    qty = fields.Float(string='Qty', default=1.0)
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Disc. %', default=0.0)
    tax_percent = fields.Float(string='Tax %', default=0.0)

    price_subtotal = fields.Float(compute='_compute_line', store=True)
    price_tax = fields.Float(compute='_compute_line', store=True)
    price_total = fields.Float(compute='_compute_line', store=True)

    currency_id = fields.Many2one(
        'res.currency', related='order_id.currency_id', store=True, readonly=True)

    @api.depends('qty', 'price_unit', 'discount', 'tax_percent')
    def _compute_line(self):
        for rec in self:
            gross = rec.qty * rec.price_unit
            net = gross * (1 - (rec.discount or 0.0) / 100.0)
            rec.price_subtotal = net
            rec.price_tax = net * (rec.tax_percent or 0.0) / 100.0
            rec.price_total = rec.price_subtotal + rec.price_tax

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.name = self.service_id.name
            self.price_unit = self.service_id._get_live_price()
            self.tax_percent = self.service_id.tax_percent
