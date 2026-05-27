from odoo import models, fields, api, _


class OEICU(models.Model):
    _name = 'oeh.icu'
    _description = 'ICU Critical Care'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'patient_id'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    apache_score = fields.Integer()
    sofa_score = fields.Integer()
    oxygen_level = fields.Float()
    notes = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='ICU Ref', default='New', readonly=True, copy=False, index=True)
    bed_id = fields.Many2one('oeh.bed', string='ICU Bed', tracking=True)
    attending_doctor_id = fields.Many2one('oeh.doctor', string='Intensivist', tracking=True)
    nurse_in_charge = fields.Char(string='Nurse In-Charge')
    admission_date = fields.Datetime(default=fields.Datetime.now, tracking=True)

    status = fields.Selection([
        ('monitoring', 'Monitoring'),
        ('critical', 'Critical'),
        ('stable', 'Stable'),
        ('recovered', 'Recovered'),
        ('discharged', 'Discharged'),
    ], default='monitoring', tracking=True)
    is_critical = fields.Boolean(string='Critical Alert', tracking=True)

    # Equipment support structure
    on_ventilator = fields.Boolean(string='On Ventilator')
    on_monitor = fields.Boolean(string='On Monitor')

    # Vitals integration structure
    heart_rate = fields.Integer(string='Heart Rate (bpm)')
    bp_systolic = fields.Integer(string='BP Systolic')
    bp_diastolic = fields.Integer(string='BP Diastolic')
    temperature = fields.Float(string='Temperature (°C)')
    respiratory_rate = fields.Integer(string='Respiratory Rate')
    shift_notes = fields.Text(string='Shift Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.icu') or 'New'
        return super().create(vals_list)

    @api.depends('name', 'patient_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'New':
                rec.display_name = '%s - %s' % (rec.name, rec.patient_id.display_name or '')
            else:
                rec.display_name = rec.patient_id.display_name or _('ICU Record')

    # ---- Workflow ----
    def action_set_critical(self):
        self.write({'status': 'critical', 'is_critical': True})

    def action_set_stable(self):
        self.write({'status': 'stable', 'is_critical': False})

    def action_set_recovered(self):
        self.write({'status': 'recovered'})

    def action_discharge(self):
        for rec in self:
            rec.status = 'discharged'
            if rec.bed_id:
                rec.bed_id.write({'status': 'cleaning', 'current_patient_id': False})
