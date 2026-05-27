from odoo import models, fields, api, _


class OENursing(models.Model):
    _name = 'oeh.nursing'
    _description = 'Nursing Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'patient_id'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    nurse = fields.Char(required=True)
    care_plan = fields.Text()
    notes = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='Plan Ref', default='New', readonly=True, copy=False, index=True)
    plan_date = fields.Date(default=fields.Date.context_today, tracking=True)
    shift = fields.Selection([
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('night', 'Night'),
    ], default='morning', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
    ], default='draft', tracking=True)
    medication_notes = fields.Text(string='Medication Administration')
    vitals_checked = fields.Boolean(string='Vitals Checked')
    medication_given = fields.Boolean(string='Medication Administered')
    hygiene_done = fields.Boolean(string='Hygiene/Care Done')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.nursing') or 'New'
        return super().create(vals_list)

    @api.depends('name', 'patient_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'New':
                rec.display_name = '%s - %s' % (rec.name, rec.patient_id.display_name or '')
            else:
                rec.display_name = rec.patient_id.display_name or _('Nursing Plan')

    # ---- Workflow ----
    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reset(self):
        self.write({'state': 'draft'})
