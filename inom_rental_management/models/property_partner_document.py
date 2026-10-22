from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PropertyPartnerDocument(models.Model):
    _name = 'property.partner.document'
    _description = 'Owner and Tenant Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'partner_id, document_type, id'
    _check_company_auto = True

    name = fields.Char(string='Document', required=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Owner / Tenant', required=True, index=True, ondelete='cascade',
        tracking=True, check_company=True,
        domain="['|', '|', ('is_property_owner', '=', True), ('is_tenant', '=', True), ('is_property_buyer', '=', True)]",
    )
    document_type = fields.Selection(
        selection=[
            ('identity', 'Identity Proof'),
            ('address', 'Address Proof'),
            ('tax', 'Tax ID'),
            ('ownership', 'Ownership Proof'),
            ('bank', 'Bank Details'),
            ('agreement', 'Agreement'),
            ('other', 'Other'),
        ],
        required=True, default='identity', tracking=True,
    )
    document_number = fields.Char(tracking=True)
    issue_date = fields.Date()
    expiry_date = fields.Date(tracking=True)
    file = fields.Binary(attachment=True)
    file_name = fields.Char()
    note = fields.Text()
    company_id = fields.Many2one(
        'res.company', index=True,
        default=lambda self: self.env.company,
    )
    is_expired = fields.Boolean(compute='_compute_is_expired')

    _number_uniq = models.Constraint(
        'UNIQUE(document_type, document_number)',
        'This document number is already registered for another owner or tenant.',
    )

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for document in self:
            document.is_expired = bool(document.expiry_date and document.expiry_date < today)

    @api.constrains('issue_date', 'expiry_date')
    def _check_dates(self):
        for document in self:
            if document.issue_date and document.expiry_date and document.expiry_date <= document.issue_date:
                raise ValidationError(self.env._("The expiry date must be after the issue date."))

    @api.constrains('partner_id')
    def _check_partner_role(self):
        for document in self:
            partner = document.partner_id
            if not (partner.is_property_owner or partner.is_tenant or partner.is_property_buyer):
                raise ValidationError(self.env._(
                    "%(partner)s is not an owner, tenant or buyer: mark the contact's role first.",
                    partner=partner.display_name,
                ))
