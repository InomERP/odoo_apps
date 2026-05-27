from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OEInsurance(models.Model):

    _name = 'oeh.insurance.claim'
    _description = 'Insurance Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'patient_id'


    name = fields.Char(
        string='Claim No', default='New', readonly=True, copy=False,
        index=True, tracking=True)

    patient_id = fields.Many2one(
        'oeh.patient',
        tracking=True,
        required=True
    )

    insurance_company = fields.Char(tracking=True)

    insurance_partner_id = fields.Many2one(
        'res.partner', string='Insurance Company (Linked)', tracking=True)

    policy_number = fields.Char(tracking=True)

    claim_amount = fields.Float()

    approved_amount = fields.Float()

    coverage_percentage = fields.Float(string='Coverage %')

    patient_responsibility = fields.Float(
        compute='_compute_patient_responsibility', store=True)

    settlement_date = fields.Date(tracking=True)
    settled_amount = fields.Float(tracking=True)
    approval_notes = fields.Text()
    rejection_reason = fields.Text()
    attachment_ids = fields.Many2many(
        'ir.attachment', 'oeh_claim_attachment_rel',
        'claim_id', 'attachment_id', string='Claim Documents')

    claim_status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('settled', 'Settled')
    ], default='draft', tracking=True)

    edi_number = fields.Char()

    remarks = fields.Text()

    # ---------------- SMART BUTTON COUNTERS ----------------

    claim_count = fields.Integer(
        compute="_compute_claim_count"
    )

    @api.depends('patient_id')
    def _compute_claim_count(self):

        for rec in self:

            rec.claim_count = self.env[
                'oeh.insurance.claim'
            ].search_count([
                ('patient_id', '=', rec.patient_id.id)
            ])

    def action_view_claims(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Insurance Claims',
            'res_model': 'oeh.insurance.claim',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.patient_id.id)]
        }

    # ---------------- SEQUENCE / COMPUTES / VALIDATION ----------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'oeh.insurance.claim') or 'New'
        return super().create(vals_list)

    @api.depends('claim_amount', 'approved_amount')
    def _compute_patient_responsibility(self):
        for rec in self:
            rec.patient_responsibility = (rec.claim_amount or 0.0) - (rec.approved_amount or 0.0)

    @api.depends('name', 'patient_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.name != 'New':
                rec.display_name = '%s - %s' % (rec.name, rec.patient_id.display_name or '')
            else:
                rec.display_name = rec.patient_id.display_name or _('New Claim')

    @api.constrains('claim_amount', 'approved_amount')
    def _check_claim_amounts(self):
        for rec in self:
            if rec.claim_amount < 0 or rec.approved_amount < 0:
                raise ValidationError(_("Claim amounts cannot be negative."))
            if rec.approved_amount > rec.claim_amount and rec.claim_amount:
                raise ValidationError(_(
                    "Approved amount cannot exceed the claimed amount."))

    # ---------------- CLAIM LIFECYCLE ----------------
    def action_submit(self):
        self.write({'claim_status': 'submitted'})

    def action_review(self):
        self.write({'claim_status': 'under_review'})

    def action_approve(self):
        for rec in self:
            if rec.approved_amount <= 0:
                raise ValidationError(_(
                    "Set an approved amount before approving the claim."))
            rec.claim_status = 'approved'

    def action_reject(self):
        for rec in self:
            if not rec.rejection_reason:
                raise ValidationError(_("Please provide a rejection reason."))
            rec.claim_status = 'rejected'

    def action_settle(self):
        for rec in self:
            rec.write({
                'claim_status': 'settled',
                'settlement_date': rec.settlement_date or fields.Date.context_today(rec),
                'settled_amount': rec.settled_amount or rec.approved_amount,
            })

    def action_reset(self):
        self.write({'claim_status': 'draft'})







# from odoo import models,fields

# class OEInsurance(models.Model):

#     _name='oeh.insurance.claim'
#     _description='Insurance Claim'

#     patient_id=fields.Many2one(
#         'oeh.patient'
#     )

#     insurance_company=fields.Char()

#     policy_number=fields.Char()

#     claim_amount=fields.Float()

#     approved_amount=fields.Float()

#     claim_status=fields.Selection([
#         ('draft','Draft'),
#         ('submitted','Submitted'),
#         ('approved','Approved'),
#         ('rejected','Rejected')
#     ])

#     edi_number=fields.Char()

#     remarks=fields.Text()