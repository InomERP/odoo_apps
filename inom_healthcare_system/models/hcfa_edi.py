from odoo import models, fields, api, _


class OEHCFA(models.Model):

    _name = 'oeh.hcfa'
    _description = 'HCFA EDI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ---- Existing fields (preserved) ----
    patient_id = fields.Many2one(
        'oeh.patient',
        required=True
    )

    claim_id = fields.Many2one(
        'oeh.insurance.claim',
        required=True
    )

    form_type = fields.Selection([
        ('hcfa1500', 'HCFA-1500'),
        ('edi837p', 'EDI 837P')
    ], required=True)

    submission_date = fields.Date()

    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    # ---- Professional additions ----
    name = fields.Char(
        string='Form Ref', default='New', readonly=True, copy=False,
        index=True, tracking=True)

    # Insurance auto-fill from the linked claim
    insurance_company = fields.Char(
        related='claim_id.insurance_company', string='Insurance Company',
        readonly=True)
    policy_number = fields.Char(related='claim_id.policy_number', readonly=True)
    claim_amount = fields.Float(related='claim_id.claim_amount', readonly=True)

    diagnosis_id = fields.Many2one('oeh.icd', string='Diagnosis (ICD)')
    procedure_description = fields.Char(string='Procedure / Service')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'oeh.hcfa') or 'New'
        return super().create(vals_list)

    @api.depends('name', 'patient_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'New':
                rec.display_name = rec.name
            else:
                rec.display_name = rec.patient_id.display_name or _('New Form')

    # ---- Workflow ----
    def action_send(self):
        for rec in self:
            rec.write({
                'status': 'sent',
                'submission_date': rec.submission_date or fields.Date.context_today(rec),
            })

    def action_accept(self):
        self.write({'status': 'accepted'})

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_reset(self):
        self.write({'status': 'draft'})
