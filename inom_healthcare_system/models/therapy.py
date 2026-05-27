from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEPhysicalTherapy(models.Model):

    _name = 'oeh.therapy'
    _description = 'Physical Therapy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'therapist'
    _order = 'session_date desc, id desc'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    therapist = fields.Char(required=True, tracking=True)
    session_date = fields.Date(required=True, tracking=True)
    treatment_plan = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='Session Ref', default='New', readonly=True, copy=False, index=True)
    session_no = fields.Integer(string='Session No.')
    session_type = fields.Selection([
        ('assessment', 'Initial Assessment'),
        ('treatment', 'Treatment'),
        ('review', 'Review'),
    ], default='treatment')
    duration = fields.Float(string='Duration (min)')

    state = fields.Selection([
        ('draft', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    # Assessments / progress
    pain_level = fields.Integer(string='Pain Level (0-10)')
    mobility_score = fields.Integer(string='Mobility Score (0-10)')
    progress_notes = fields.Text()
    exercises = fields.Text(string='Prescribed Exercises')
    rehab_notes = fields.Text(string='Rehabilitation Notes')
    followup_date = fields.Date(string='Next Session')

    # Billing
    fee = fields.Float(string='Session Fee')
    billing_id = fields.Many2one('oeh.billing', string='Bill', copy=False)
    billing_count = fields.Integer(compute='_compute_billing_count')
    session_count = fields.Integer(compute='_compute_session_count')

    def _compute_billing_count(self):
        for rec in self:
            rec.billing_count = 1 if rec.billing_id else 0

    def _compute_session_count(self):
        for rec in self:
            rec.session_count = self.search_count([('patient_id', '=', rec.patient_id.id)]) \
                if rec.patient_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.therapy') or 'New'
        return super().create(vals_list)

    @api.constrains('pain_level', 'mobility_score')
    def _check_scores(self):
        for rec in self:
            if rec.pain_level and not (0 <= rec.pain_level <= 10):
                raise ValidationError(_("Pain level must be between 0 and 10."))
            if rec.mobility_score and not (0 <= rec.mobility_score <= 10):
                raise ValidationError(_("Mobility score must be between 0 and 10."))

    # ---- Workflow ----
    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

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
