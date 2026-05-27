from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MedicalCertificate(models.Model):

    _name = 'oeh.certificate'
    _description = 'Medical Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'patient_id'
    _order = 'id desc'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one('oeh.patient', required=True, tracking=True)
    issue_date = fields.Date(tracking=True)
    valid_until = fields.Date(tracking=True)
    details = fields.Html()

    # ---- Professional additions ----
    name = fields.Char(string='Certificate No.', default='New', readonly=True, copy=False, index=True)
    doctor_id = fields.Many2one('oeh.doctor', string='Issuing Doctor', tracking=True)
    certificate_type = fields.Selection([
        ('fitness', 'Fitness Certificate'),
        ('sick', 'Sick Leave'),
        ('medical_leave', 'Medical Leave'),
    ], default='sick', tracking=True)
    reason = fields.Char(string='Reason / Diagnosis')
    leave_days = fields.Integer(string='No. of Days')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    is_expired = fields.Boolean(compute='_compute_is_expired', store=True)

    # Reference / signature structure
    reference = fields.Char(string='Verification Reference', copy=False,
                            help="QR / verification reference for authenticity checks")
    signed_by = fields.Char(string='Signed By')
    signed_date = fields.Date()
    signature = fields.Binary(string='Digital Signature', attachment=True)

    @api.depends('valid_until')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expired = bool(rec.valid_until and rec.valid_until < today)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('oeh.certificate') or 'New'
        return super().create(vals_list)

    @api.constrains('issue_date', 'valid_until')
    def _check_dates(self):
        for rec in self:
            if rec.issue_date and rec.valid_until and rec.valid_until < rec.issue_date:
                raise ValidationError(_("Valid-until date cannot be earlier than the issue date."))

    # ---- Workflow ----
    def action_issue(self):
        for rec in self:
            if not rec.doctor_id:
                raise ValidationError(_("Assign an issuing doctor before issuing the certificate."))
            vals = {'state': 'issued'}
            if not rec.issue_date:
                vals['issue_date'] = fields.Date.context_today(self)
            if not rec.reference:
                vals['reference'] = rec.name
            rec.write(vals)

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset(self):
        self.write({'state': 'draft'})
