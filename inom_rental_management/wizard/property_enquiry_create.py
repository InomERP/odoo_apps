from odoo import api, fields, models
from odoo.exceptions import UserError


class PropertyEnquiryCreate(models.TransientModel):
    _name = 'property.enquiry.create'
    _description = 'Record a Property Enquiry'

    property_id = fields.Many2one('property.property', required=True)
    property_for = fields.Selection(
        selection=[('rent', 'Rent'), ('sale', 'Sale')], string='Enquiry For', required=True,
        compute='_compute_property_for', store=True, readonly=False, precompute=True,
    )
    company_id = fields.Many2one(related='property_id.company_id')
    company_currency = fields.Many2one(related='property_id.currency_id')
    partner_id = fields.Many2one('res.partner', string='Customer')
    contact_name = fields.Char(help="For a prospect not yet in your contacts.")
    email_from = fields.Char(string='Email')
    phone = fields.Char()
    ask_price = fields.Monetary(string='Asking Price', currency_field='company_currency')
    user_id = fields.Many2one(
        'res.users', string='Responsible Agent',
        compute='_compute_user_id', store=True, readonly=False, precompute=True, compute_sudo=False,
        domain=lambda self: [('share', '=', False), ('all_group_ids', 'in', self.env.ref('sales_team.group_sale_salesman').ids)],
    )
    description = fields.Html(string='Notes')
    duplicate_count = fields.Integer(compute='_compute_duplicates')
    duplicate_summary = fields.Text(string='Open Enquiries', compute='_compute_duplicates')
    create_anyway = fields.Boolean(help="Record a new enquiry although an open one exists for this customer and property.")

    @api.depends('property_id')
    def _compute_property_for(self):
        for wizard in self:
            wizard.property_for = wizard.property_id.property_for or wizard.property_for

    @api.depends('property_id')
    def _compute_user_id(self):
        for wizard in self:
            wizard.user_id = self.env['crm.lead']._default_property_agent(wizard.property_id) or self.env.user

    def _get_duplicates(self):
        self.ensure_one()
        return self.env['crm.lead']._find_open_property_enquiries(
            self.property_id, self.property_for, self.partner_id, self.email_from,
        )

    @api.depends('property_id', 'property_for', 'partner_id', 'email_from')
    def _compute_duplicates(self):
        for wizard in self:
            duplicates = wizard._get_duplicates()
            wizard.duplicate_count = len(duplicates)
            wizard.duplicate_summary = duplicates._property_enquiry_summary()

    def action_open_existing(self):
        self.ensure_one()
        lead = self._get_duplicates()[:1]
        if not lead:
            raise UserError(self.env._("No open enquiry matches this customer and property."))
        if not lead.with_env(self.env).has_access('read'):
            raise UserError(self.env._(
                "The open enquiry %(lead)s is handled by %(user)s and you cannot open it. Ask them to follow up.",
                lead=lead.name, user=lead.user_id.name or self.env._("nobody"),
            ))
        return {'type': 'ir.actions.act_window', 'res_model': 'crm.lead', 'view_mode': 'form', 'res_id': lead.id}

    def action_create(self):
        self.ensure_one()
        if not (self.partner_id or self.contact_name or self.email_from):
            raise UserError(self.env._("Enter the customer, or at least the prospect's name or email."))
        duplicates = self._get_duplicates()
        if duplicates and not self.create_anyway:
            lead = duplicates[:1]
            raise UserError(self.env._(
                "%(customer)s already has an open enquiry for %(property)s: %(lead)s, handled by %(user)s. "
                "Open it, or tick Create Anyway.",
                customer=self.partner_id.display_name or self.contact_name or self.email_from,
                property=self.property_id.display_name, lead=lead.name,
                user=lead.user_id.name or self.env._("nobody"),
            ))
        purpose = dict(self._fields['property_for']._description_selection(self.env))[self.property_for]
        lead = self.env['crm.lead'].create({
            'name': self.env._("%(purpose)s enquiry: %(property)s", purpose=purpose, property=self.property_id.display_name),
            'type': 'opportunity',
            'property_id': self.property_id.id,
            'property_for': self.property_for,
            'partner_id': self.partner_id.id,
            'contact_name': self.contact_name if not self.partner_id else False,
            'email_from': self.email_from or self.partner_id.email,
            'phone': self.phone or self.partner_id.phone,
            'ask_price': self.ask_price,
            'user_id': self.user_id.id,
            'company_id': self.property_id.company_id.id,
            'description': self.description,
        })
        return {'type': 'ir.actions.act_window', 'res_model': 'crm.lead', 'view_mode': 'form', 'res_id': lead.id}
