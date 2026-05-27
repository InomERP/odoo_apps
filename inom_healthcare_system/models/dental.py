from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEDental(models.Model):

    _name = 'oeh.dental'
    _description = 'Dental Practice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'tooth_issue'
    _order = 'id desc'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    tooth_issue = fields.Char(required=True, tracking=True)
    procedure = fields.Char()
    notes = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='Case Ref', default='New', readonly=True, copy=False, index=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    dentist = fields.Char(string='Dentist')

    # Charting / tooth structure
    tooth_number = fields.Char(string='Tooth Number', help="e.g. FDI/Universal numbering")
    quadrant = fields.Selection([
        ('ur', 'Upper Right'),
        ('ul', 'Upper Left'),
        ('lr', 'Lower Right'),
        ('ll', 'Lower Left'),
    ], string='Quadrant')
    procedure_type = fields.Selection([
        ('exam', 'Examination'),
        ('cleaning', 'Cleaning/Scaling'),
        ('filling', 'Filling'),
        ('extraction', 'Extraction'),
        ('root_canal', 'Root Canal'),
        ('crown', 'Crown/Bridge'),
        ('other', 'Other'),
    ], default='exam')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    treatment_plan = fields.Text()
    procedure_history = fields.Text(string='Procedure History')
    prescription_notes = fields.Text(string='Dental Prescription')
    report_reference = fields.Char(string='Imaging/Report Ref')

    # Appointment linkage (read-only reference to existing appointment module)
    appointment_id = fields.Many2one('oeh.appointment', string='Appointment')
    followup_date = fields.Date(string='Follow-up / Reminder')

    # Billing
    fee = fields.Float(string='Procedure Fee')
    billing_id = fields.Many2one('oeh.billing', string='Bill', copy=False)
    billing_count = fields.Integer(compute='_compute_billing_count')
    case_count = fields.Integer(compute='_compute_case_count')

    def _compute_billing_count(self):
        for rec in self:
            rec.billing_count = 1 if rec.billing_id else 0

    def _compute_case_count(self):
        for rec in self:
            rec.case_count = self.search_count([('patient_id', '=', rec.patient_id.id)]) \
                if rec.patient_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.dental') or 'New'
        return super().create(vals_list)

    @api.constrains('fee')
    def _check_fee(self):
        for rec in self:
            if rec.fee < 0:
                raise ValidationError(_("Procedure fee cannot be negative."))

    # ---- Workflow ----
    def action_plan(self):
        self.write({'state': 'planned'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_create_billing(self):
        self.ensure_one()
        if not self.billing_id:
            self.billing_id = self.env['oeh.billing'].create({
                'patient_id': self.patient_id.id,
                'total_amount': self.fee or 0.0,
            }).id
        return {
            'type': 'ir.actions.act_window', 'name': _('Bill'),
            'res_model': 'oeh.billing', 'res_id': self.billing_id.id,
            'view_mode': 'form', 'target': 'current',
        }
