from odoo import models, fields, api, _


class Prescription(models.Model):

    _name = 'oeh.prescription'
    _description = 'Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'medicine'
    _order = 'date desc, id desc'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    doctor_id = fields.Many2one('oeh.doctor', required=True, tracking=True)
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    medicine = fields.Char(required=True, tracking=True)
    dosage = fields.Char(required=True)
    instruction = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='Prescription No.', default='New', readonly=True, copy=False, index=True)
    diagnosis_id = fields.Many2one('oeh.icd', string='Diagnosis (ICD)')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('verified', 'Verified'),
        ('issued', 'Issued'),
        ('dispensed', 'Dispensed'),
    ], default='draft', tracking=True)

    # Doctor verification
    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True, copy=False)
    verified_date = fields.Datetime(readonly=True, copy=False)

    # Safety structure
    allergy_warning = fields.Text(string='Allergy / Interaction Notes')

    # Refill tracking
    refill_allowed = fields.Boolean(string='Refill Allowed')
    refill_count = fields.Integer(string='Refills', default=0)

    # Pharmacy / history linkage (read-only)
    dispense_count = fields.Integer(compute='_compute_dispense_count')
    prescription_count = fields.Integer(compute='_compute_prescription_count')

    def _compute_dispense_count(self):
        Dispense = self.env['oeh.prescription.dispense']
        for rec in self:
            rec.dispense_count = Dispense.search_count([('prescription_id', '=', rec.id)])

    def _compute_prescription_count(self):
        for rec in self:
            rec.prescription_count = self.search_count([('patient_id', '=', rec.patient_id.id)]) \
                if rec.patient_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.prescription') or 'New'
        return super().create(vals_list)

    @api.depends('name', 'medicine')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'New':
                rec.display_name = '%s - %s' % (rec.name, rec.medicine or '')
            else:
                rec.display_name = rec.medicine or _('Prescription')

    # ---- Workflow ----
    def action_verify(self):
        for rec in self:
            rec.write({
                'state': 'verified',
                'verified_by': self.env.user.id,
                'verified_date': fields.Datetime.now(),
            })

    def action_issue(self):
        self.write({'state': 'issued'})

    def action_dispense(self):
        self.write({'state': 'dispensed'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_view_dispenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Dispenses'),
            'res_model': 'oeh.prescription.dispense', 'view_mode': 'list,form',
            'domain': [('prescription_id', '=', self.id)],
            'context': {'default_prescription_id': self.id,
                        'default_patient_id': self.patient_id.id},
        }

    def action_view_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Prescription History'),
            'res_model': 'oeh.prescription', 'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.patient_id.id)],
            'context': {'default_patient_id': self.patient_id.id},
        }
