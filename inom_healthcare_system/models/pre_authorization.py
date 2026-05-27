from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEPreAuth(models.Model):

    _name = 'oeh.pre.authorization'
    _description = 'Pre Authorization'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one(
        'oeh.patient',
        required=True
    )

    insurance_company = fields.Char(required=True)

    procedure_name = fields.Char(required=True)

    requested_amount = fields.Float(required=True)

    approved_amount = fields.Float()

    authorization_no = fields.Char()

    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ], required=True, default='draft', tracking=True)

    notes = fields.Text()

    # ---- Professional additions ----
    name = fields.Char(
        string='Pre-Auth Ref', default='New', readonly=True, copy=False,
        index=True, tracking=True)

    doctor_id = fields.Many2one('oeh.doctor', string='Requesting Doctor')
    insurance_partner_id = fields.Many2one(
        'res.partner', string='Insurance Company (Linked)')
    policy_number = fields.Char()
    justification = fields.Text(string='Medical Justification')
    request_date = fields.Date(default=fields.Date.context_today, tracking=True)
    decision_date = fields.Date(tracking=True)
    valid_from = fields.Date()
    valid_until = fields.Date(tracking=True)
    is_expired = fields.Boolean(compute='_compute_is_expired')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'oeh_preauth_attachment_rel',
        'preauth_id', 'attachment_id', string='Supporting Documents')

    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expired = bool(rec.valid_until and rec.valid_until < today)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'oeh.pre.authorization') or 'New'
        return super().create(vals_list)

    @api.depends('name', 'procedure_name')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'New':
                rec.display_name = '%s - %s' % (rec.name, rec.procedure_name or '')
            else:
                rec.display_name = rec.procedure_name or _('New Request')

    @api.constrains('requested_amount', 'approved_amount')
    def _check_preauth_amounts(self):
        for rec in self:
            if rec.requested_amount < 0 or rec.approved_amount < 0:
                raise ValidationError(_("Amounts cannot be negative."))
            if rec.approved_amount > rec.requested_amount and rec.requested_amount:
                raise ValidationError(_(
                    "Approved amount cannot exceed the requested amount."))

    @api.constrains('valid_from', 'valid_until')
    def _check_validity_dates(self):
        for rec in self:
            if rec.valid_from and rec.valid_until and rec.valid_until < rec.valid_from:
                raise ValidationError(_(
                    "'Valid Until' cannot be earlier than 'Valid From'."))

    # ---- Workflow ----
    def action_submit(self):
        self.write({'status': 'pending', 'request_date': fields.Date.context_today(self)})

    def action_approve(self):
        for rec in self:
            vals = {'status': 'approved',
                    'decision_date': fields.Date.context_today(rec)}
            if not rec.authorization_no:
                vals['authorization_no'] = self.env['ir.sequence'].next_by_code(
                    'oeh.pre.authorization') or rec.name
            rec.write(vals)

    def action_reject(self):
        self.write({'status': 'rejected',
                    'decision_date': fields.Date.context_today(self)})

    def action_expire(self):
        self.write({'status': 'expired'})

    def action_reset(self):
        self.write({'status': 'draft'})
