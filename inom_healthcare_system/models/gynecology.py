from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class OEGynecology(models.Model):

    _name = 'oeh.gynecology'
    _description = 'Gynecology'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'patient_id'
    _order = 'id desc'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    # original keys (yes/no) preserved
    pregnancy_status = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], required=True, default='no', tracking=True)
    last_cycle = fields.Date(string='LMP (Last Menstrual Period)')
    notes = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='Case Ref', default='New', readonly=True, copy=False, index=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    consultant = fields.Char(string='Consultant')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('consultation', 'In Consultation'),
        ('followup', 'Follow-up'),
        ('closed', 'Closed'),
    ], default='draft', tracking=True)

    # Menstrual history
    cycle_length = fields.Integer(string='Cycle Length (days)')
    cycle_regular = fields.Boolean(string='Regular Cycle')
    menstrual_notes = fields.Text()

    # Obstetric history (GPA)
    gravida = fields.Integer(string='Gravida (G)')
    para = fields.Integer(string='Para (P)')
    abortions = fields.Integer(string='Abortions (A)')

    # Pregnancy / ANC tracking
    edd = fields.Date(string='EDD (Expected Delivery)', compute='_compute_pregnancy', store=True)
    gestational_age = fields.Integer(string='Gestational Age (weeks)',
                                     compute='_compute_pregnancy')
    anc_visit_no = fields.Integer(string='ANC Visit No.')
    ultrasound_notes = fields.Text(string='Ultrasound Findings')
    report_reference = fields.Char(string='Report Reference')

    # Delivery planning
    delivery_type = fields.Selection([
        ('normal', 'Normal'),
        ('cesarean', 'Cesarean'),
        ('undecided', 'Undecided'),
    ], default='undecided')
    delivery_date = fields.Date(string='Planned/Actual Delivery')
    delivery_plan = fields.Text()

    # Clinical / hormonal tracking
    bp = fields.Char(string='Blood Pressure')
    weight = fields.Float(string='Weight (kg)')
    hb = fields.Float(string='Hemoglobin (g/dL)')
    followup_date = fields.Date(string='Follow-up Date')

    visit_count = fields.Integer(compute='_compute_visit_count')

    @api.depends('pregnancy_status', 'last_cycle')
    def _compute_pregnancy(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.pregnancy_status == 'yes' and rec.last_cycle:
                rec.edd = rec.last_cycle + timedelta(days=280)
                rec.gestational_age = max((today - rec.last_cycle).days // 7, 0)
            else:
                rec.edd = False
                rec.gestational_age = 0

    def _compute_visit_count(self):
        for rec in self:
            rec.visit_count = self.search_count([('patient_id', '=', rec.patient_id.id)]) \
                if rec.patient_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.gynecology') or 'New'
        return super().create(vals_list)

    @api.constrains('gravida', 'para', 'abortions', 'cycle_length')
    def _check_obstetric(self):
        for rec in self:
            if rec.gravida < 0 or rec.para < 0 or rec.abortions < 0:
                raise ValidationError(_("Obstetric counts (G/P/A) cannot be negative."))
            if rec.cycle_length and rec.cycle_length < 0:
                raise ValidationError(_("Cycle length cannot be negative."))

    # ---- Workflow ----
    def action_start_consultation(self):
        self.write({'state': 'consultation'})

    def action_followup(self):
        self.write({'state': 'followup'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_view_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maternal Care History'),
            'res_model': 'oeh.gynecology',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.patient_id.id)],
            'context': {'default_patient_id': self.patient_id.id},
        }
