from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Consent(models.Model):

    _name = 'oeh.consent'
    _description = 'Digital Consent'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'consent_type'
    _order = 'id desc'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    consent_type = fields.Char(required=True, tracking=True)
    signed = fields.Boolean(tracking=True)
    notes = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(string='Consent Ref', default='New', readonly=True, copy=False, index=True)
    consent_date = fields.Date(default=fields.Date.context_today, tracking=True)
    valid_until = fields.Date()
    procedure = fields.Char(string='Procedure / Reason')
    treatment_id = fields.Many2one('oeh.treatment', string='Related Treatment')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Signature'),
        ('signed', 'Signed'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    # Patient / guardian verification
    guardian_name = fields.Char(string='Guardian Name')
    guardian_relation = fields.Selection([
        ('self', 'Self'),
        ('parent', 'Parent'),
        ('spouse', 'Spouse'),
        ('guardian', 'Legal Guardian'),
    ], default='self')

    # Signature / template structure
    consent_template = fields.Html(string='Consent Text / Template')
    signed_by = fields.Char(string='Signed By')
    signed_date = fields.Datetime()
    signature = fields.Binary(string='Signature', attachment=True)
    is_expired = fields.Boolean(compute='_compute_is_expired', store=True)

    @api.depends('valid_until')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expired = bool(rec.valid_until and rec.valid_until < today)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.consent') or 'New'
        return super().create(vals_list)

    @api.constrains('consent_date', 'valid_until')
    def _check_dates(self):
        for rec in self:
            if rec.consent_date and rec.valid_until and rec.valid_until < rec.consent_date:
                raise ValidationError(_("Validity date cannot be earlier than the consent date."))

    # ---- Workflow ----
    def action_request(self):
        self.write({'state': 'pending'})

    def action_sign(self):
        for rec in self:
            rec.write({
                'state': 'signed',
                'signed': True,
                'signed_date': fields.Datetime.now(),
            })

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset(self):
        self.write({'state': 'draft', 'signed': False})
