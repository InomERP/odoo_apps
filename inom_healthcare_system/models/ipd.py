from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEIPD(models.Model):
    _name = 'oeh.ipd'
    _description = 'IPD Admission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ---- Existing fields (preserved) ----
    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    bed_id = fields.Many2one('oeh.bed', required=True, tracking=True)
    admission_date = fields.Datetime(tracking=True)
    discharge_date = fields.Datetime(tracking=True)

    # NOTE: original keys (admitted/discharged) kept; new stages appended.
    status = fields.Selection([
        ('admitted', 'Admitted'),
        ('under_treatment', 'Under Treatment'),
        ('discharged', 'Discharged'),
        ('closed', 'Closed'),
    ], default='admitted', tracking=True)

    # ---- Professional additions ----
    ward_id = fields.Many2one(related='bed_id.ward_id', string='Ward', store=True, readonly=True)
    attending_doctor_id = fields.Many2one('oeh.doctor', string='Attending Doctor', tracking=True)
    nurse_in_charge = fields.Char(string='Nurse In-Charge')
    reason = fields.Text(string='Reason for Admission')
    diagnosis = fields.Text()
    discharge_summary = fields.Html(string='Discharge Summary')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    billing_id = fields.Many2one('oeh.billing', string='Bill', copy=False)
    billing_count = fields.Integer(compute='_compute_billing_count')

    def _compute_billing_count(self):
        for rec in self:
            rec.billing_count = 1 if rec.billing_id else 0

    # ---- Existing create (preserved) ----
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.ipd') or 'New'
        records = super().create(vals_list)
        for rec in records:
            if rec.status == 'admitted' and rec.bed_id:
                rec.bed_id.write({
                    'status': 'occupied',
                    'current_patient_id': rec.patient_id.id,
                })
        return records

    @api.constrains('admission_date', 'discharge_date')
    def _check_dates(self):
        for rec in self:
            if rec.admission_date and rec.discharge_date and rec.discharge_date < rec.admission_date:
                raise ValidationError(_("Discharge date cannot be earlier than admission date."))

    # ---- Admission lifecycle (with bed automation) ----
    def action_admit(self):
        for rec in self:
            rec.status = 'admitted'
            if not rec.admission_date:
                rec.admission_date = fields.Datetime.now()
            if rec.bed_id:
                rec.bed_id.write({
                    'status': 'occupied',
                    'current_patient_id': rec.patient_id.id,
                })

    def action_start_treatment(self):
        self.write({'status': 'under_treatment'})

    def action_discharge(self):
        for rec in self:
            rec.status = 'discharged'
            if not rec.discharge_date:
                rec.discharge_date = fields.Datetime.now()
            if rec.bed_id:
                rec.bed_id.write({'status': 'cleaning', 'current_patient_id': False})

    def action_close(self):
        self.write({'status': 'closed'})

    def action_reset(self):
        self.write({'status': 'admitted'})

    # ---- Billing integration (creates a finance bill; does not modify finance code) ----
    def action_create_billing(self):
        self.ensure_one()
        if not self.billing_id:
            self.billing_id = self.env['oeh.billing'].create({
                'patient_id': self.patient_id.id,
                'doctor_id': self.attending_doctor_id.id if self.attending_doctor_id else False,
                'total_amount': 0.0,
            }).id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bill'),
            'res_model': 'oeh.billing',
            'res_id': self.billing_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_bed(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'oeh.bed',
            'res_id': self.bed_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
