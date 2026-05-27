from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEPediatric(models.Model):
    _name = 'oeh.pediatric'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Pediatric Care'
    _rec_name = 'name'
    _order = 'date desc, id desc'

    # ---- Existing fields (preserved) ----
    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    age = fields.Integer(tracking=True)
    height = fields.Float(string='Height (cm)')
    weight = fields.Float(string='Weight (kg)')
    vaccine_notes = fields.Text()

    # ---- Visit / guardian ----
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    guardian_name = fields.Char(string='Parent/Guardian')
    guardian_phone = fields.Char(string='Guardian Phone')
    guardian_relation = fields.Selection([
        ('mother', 'Mother'),
        ('father', 'Father'),
        ('guardian', 'Guardian'),
    ], default='mother')

    # ---- Growth / vitals ----
    birth_weight = fields.Float(string='Birth Weight (kg)')
    head_circumference = fields.Float(string='Head Circumference (cm)')
    temperature = fields.Float(string='Temperature (°C)')
    heart_rate = fields.Integer(string='Heart Rate (bpm)')
    respiratory_rate = fields.Integer(string='Respiratory Rate')
    bmi = fields.Float(compute='_compute_bmi', store=True, string='BMI')
    bmi_status = fields.Selection([
        ('underweight', 'Underweight'),
        ('normal', 'Normal'),
        ('overweight', 'Overweight'),
    ], compute='_compute_bmi', store=True)

    # ---- Development milestones ----
    can_sit = fields.Boolean(string='Can Sit')
    can_walk = fields.Boolean(string='Can Walk')
    can_talk = fields.Boolean(string='Can Talk')
    milestone_notes = fields.Text(string='Development Notes')

    # ---- Vaccination schedule ----
    next_vaccine_date = fields.Date(string='Next Vaccine Due')
    vaccine_status = fields.Selection([
        ('unknown', 'Not Scheduled'),
        ('up_to_date', 'Up To Date'),
        ('due', 'Due Soon'),
        ('overdue', 'Overdue'),
    ], compute='_compute_vaccine_status', store=True)

    # ---- Prescription / follow-up ----
    medication = fields.Char(string='Medication')
    prescription_notes = fields.Text()
    followup_date = fields.Date(string='Follow-up Date')

    state = fields.Selection([
        ('draft', 'New'),
        ('consultation', 'In Consultation'),
        ('done', 'Completed'),
    ], default='draft', tracking=True)

    visit_count = fields.Integer(compute='_compute_visit_count')

    @api.depends('height', 'weight')
    def _compute_bmi(self):
        for rec in self:
            if rec.height and rec.weight:
                m = rec.height / 100.0
                rec.bmi = rec.weight / (m * m) if m else 0.0
            else:
                rec.bmi = 0.0
            if not rec.bmi:
                rec.bmi_status = False
            elif rec.bmi < 18.5:
                rec.bmi_status = 'underweight'
            elif rec.bmi <= 25.0:
                rec.bmi_status = 'normal'
            else:
                rec.bmi_status = 'overweight'

    @api.depends('next_vaccine_date')
    def _compute_vaccine_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.next_vaccine_date:
                rec.vaccine_status = 'unknown'
            elif rec.next_vaccine_date < today:
                rec.vaccine_status = 'overdue'
            elif (rec.next_vaccine_date - today).days <= 30:
                rec.vaccine_status = 'due'
            else:
                rec.vaccine_status = 'up_to_date'

    def _compute_visit_count(self):
        for rec in self:
            rec.visit_count = self.search_count([('patient_id', '=', rec.patient_id.id)]) \
                if rec.patient_id else 0

    # ---- Validations ----
    @api.constrains('age', 'height', 'weight')
    def _check_pediatric_values(self):
        for rec in self:
            if rec.age and (rec.age < 0 or rec.age > 18):
                raise ValidationError(_("Pediatric age must be between 0 and 18."))
            if rec.height < 0 or rec.weight < 0:
                raise ValidationError(_("Height and weight cannot be negative."))

    # ---- Existing create (preserved) ----
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.specialty') or 'New'
        return super().create(vals_list)

    # ---- Workflow ----
    def action_start_consultation(self):
        self.write({'state': 'consultation'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_view_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pediatric History'),
            'res_model': 'oeh.pediatric',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.patient_id.id)],
            'context': {'default_patient_id': self.patient_id.id},
        }
