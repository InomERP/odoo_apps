from odoo import models, fields, api, _


class OEEmergency(models.Model):
    _name = 'oeh.emergency'
    _description = 'Emergency & Triage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'patient_id'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    # original keys (low/medium/high) kept for dashboard compatibility
    triage_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'Critical'),
    ], required=True, default='medium', tracking=True)
    symptoms = fields.Text()
    notes = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='ER Ref', default='New', readonly=True, copy=False, index=True)
    arrival_time = fields.Datetime(default=fields.Datetime.now, tracking=True)
    attending_doctor_id = fields.Many2one('oeh.doctor', string='Attending Doctor', tracking=True)
    triage_color = fields.Selection([
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('red', 'Red'),
    ], compute='_compute_triage_color', store=True)
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('in_treatment', 'In Treatment'),
        ('admitted', 'Admitted'),
        ('discharged', 'Discharged'),
    ], default='waiting', tracking=True)
    ipd_id = fields.Many2one('oeh.ipd', string='Admission', copy=False, readonly=True)

    @api.depends('triage_level')
    def _compute_triage_color(self):
        mapping = {'low': 'green', 'medium': 'yellow', 'high': 'red'}
        for rec in self:
            rec.triage_color = mapping.get(rec.triage_level, 'yellow')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.emergency') or 'New'
        return super().create(vals_list)

    # ---- Triage workflow ----
    def action_start_treatment(self):
        self.write({'state': 'in_treatment'})

    def action_discharge(self):
        self.write({'state': 'discharged'})

    def action_admit_ipd(self):
        """Quick admission: open a pre-filled IPD admission for this patient."""
        self.ensure_one()
        self.state = 'admitted'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Admit Patient'),
            'res_model': 'oeh.ipd',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_patient_id': self.patient_id.id},
        }
