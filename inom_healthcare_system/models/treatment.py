from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Treatment(models.Model):

    _name = 'oeh.treatment'
    _description = 'Treatment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'treatment_name'
    _order = 'id desc'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    treatment_name = fields.Char(required=True, tracking=True)
    procedure = fields.Text()
    notes = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='Treatment Ref', default='New', readonly=True, copy=False, index=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    doctor_id = fields.Many2one('oeh.doctor', string='Doctor', tracking=True)
    diagnosis_id = fields.Many2one('oeh.icd', string='Diagnosis (ICD)')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    treatment_plan = fields.Text()
    clinical_notes = fields.Text()
    followup_date = fields.Date(string='Follow-up Date')

    fee = fields.Float(string='Treatment Fee')
    billing_id = fields.Many2one('oeh.billing', string='Bill', copy=False)
    billing_count = fields.Integer(compute='_compute_billing_count')
    treatment_count = fields.Integer(compute='_compute_treatment_count')

    def _compute_billing_count(self):
        for rec in self:
            rec.billing_count = 1 if rec.billing_id else 0

    def _compute_treatment_count(self):
        for rec in self:
            rec.treatment_count = self.search_count([('patient_id', '=', rec.patient_id.id)]) \
                if rec.patient_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.treatment') or 'New'
        return super().create(vals_list)

    @api.constrains('fee')
    def _check_fee(self):
        for rec in self:
            if rec.fee < 0:
                raise ValidationError(_("Treatment fee cannot be negative."))

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

    def action_view_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Treatment History'),
            'res_model': 'oeh.treatment', 'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.patient_id.id)],
            'context': {'default_patient_id': self.patient_id.id},
        }

    def action_create_billing(self):
        self.ensure_one()
        if not self.billing_id:
            self.billing_id = self.env['oeh.billing'].create({
                'patient_id': self.patient_id.id,
                'doctor_id': self.doctor_id.id if self.doctor_id else False,
                'total_amount': self.fee or 0.0,
            }).id
        return {
            'type': 'ir.actions.act_window', 'name': _('Bill'),
            'res_model': 'oeh.billing', 'res_id': self.billing_id.id,
            'view_mode': 'form', 'target': 'current',
        }
