from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PropertyProperty(models.Model):
    _name = 'property.property'
    _description = 'Property'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'name, id'
    _check_company_auto = True
    _rec_names_search = ['name', 'code']

    name = fields.Char(string='Property Name', required=True, tracking=True)
    code = fields.Char(string='Reference', readonly=True, copy=False, index=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    user_id = fields.Many2one(
        'res.users', string='Responsible Agent', tracking=True, check_company=True,
        default=lambda self: self._default_user_id(),
        domain=lambda self: self._domain_user_id(),
    )
    type_id = fields.Many2one('property.type', string='Property Type', required=True, tracking=True)
    category = fields.Selection(related='type_id.category', store=True)
    property_for = fields.Selection(
        selection=[('rent', 'Rent'), ('sale', 'Sale')],
        required=True, default='rent', tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('available', 'Available'),
            ('booked', 'Booked'),
            ('rented', 'Rented'),
            ('sold', 'Sold'),
        ],
        string='Availability', required=True, default='draft', copy=False, tracking=True,
    )
    owner_id = fields.Many2one(
        'res.partner', string='Owner', tracking=True, check_company=True, ondelete='restrict',
        domain="[('is_property_owner', '=', True)]",
    )

    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(string='Postal Code')
    city = fields.Char(index=True)
    state_id = fields.Many2one(
        'res.country.state', string='State', ondelete='restrict',
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one('res.country', ondelete='restrict')

    bedrooms = fields.Integer()
    bathrooms = fields.Integer()
    furnishing = fields.Selection(
        selection=[
            ('unfurnished', 'Unfurnished'),
            ('semi_furnished', 'Semi-Furnished'),
            ('furnished', 'Fully Furnished'),
        ],
        string='Furnishing Status',
    )
    total_area = fields.Float(string='Built-up Area', digits=(16, 2))
    land_area = fields.Float(digits=(16, 2))
    area_unit = fields.Selection(
        selection=[('sq_ft', 'ft²'), ('sq_m', 'm²'), ('sq_yd', 'yd²')],
        required=True, default='sq_ft',
    )
    rent_price = fields.Monetary(string='Rental Price', tracking=True, help="Monthly rent.")
    allow_multiple_leases = fields.Boolean(
        help="Allow several active leases at the same time, for example rooms of a shared house let separately.",
    )
    sale_price = fields.Monetary(tracking=True)
    amenity_ids = fields.Many2many('property.amenity', string='Amenities')
    description = fields.Html()
    image_ids = fields.One2many('property.image', 'property_id', string='Images')

    rental_contract_ids = fields.One2many('property.rental.contract', 'property_id')
    sale_contract_ids = fields.One2many('property.sale.contract', 'property_id')
    rental_contract_count = fields.Integer(compute='_compute_contract_counts')
    sale_contract_count = fields.Integer(compute='_compute_contract_counts')
    document_count = fields.Integer(compute='_compute_document_count')
    lead_ids = fields.One2many('crm.lead', 'property_id', string='Enquiries', groups='sales_team.group_sale_salesman')
    lead_count = fields.Integer(compute='_compute_lead_count', groups='sales_team.group_sale_salesman')

    _code_company_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'The property reference must be unique per company.',
    )
    _rent_price_positive = models.Constraint(
        'CHECK(rent_price >= 0)',
        'The rent cannot be negative.',
    )
    _sale_price_positive = models.Constraint(
        'CHECK(sale_price >= 0)',
        'The sale price cannot be negative.',
    )
    _total_area_positive = models.Constraint(
        'CHECK(total_area >= 0)',
        'The area cannot be negative.',
    )
    _land_area_positive = models.Constraint(
        'CHECK(land_area >= 0)',
        'The land area cannot be negative.',
    )
    _rooms_positive = models.Constraint(
        'CHECK(bedrooms >= 0 AND bathrooms >= 0)',
        'The number of bedrooms and bathrooms cannot be negative.',
    )

    def _default_user_id(self):
        if self.env.user.has_group('inom_rental_management.group_rental_agent'):
            return self.env.user
        return False

    def _domain_user_id(self):
        agent_group = self.env.ref('inom_rental_management.group_rental_agent', raise_if_not_found=False)
        domain = [('share', '=', False)]
        if agent_group:
            domain.append(('all_group_ids', 'in', agent_group.ids))
        return domain

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for prop in self:
            prop.display_name = f'[{prop.code}] {prop.name}' if prop.code else prop.name

    @api.depends('rental_contract_ids', 'sale_contract_ids')
    def _compute_contract_counts(self):
        for prop in self:
            prop.rental_contract_count = len(prop.rental_contract_ids)
            prop.sale_contract_count = len(prop.sale_contract_ids)

    def _compute_lead_count(self):
        counts = dict(self.env['crm.lead'].with_context(active_test=False)._read_group(
            [('property_id', 'in', self.ids)], groupby=['property_id'], aggregates=['__count'],
        ))
        for prop in self:
            prop.lead_count = counts.get(prop, 0)

    def _compute_document_count(self):
        counts = dict(self.env['ir.attachment']._read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)],
            groupby=['res_id'], aggregates=['__count'],
        ))
        for prop in self:
            prop.document_count = counts.get(prop.id, 0)

    @api.constrains('category', 'bedrooms', 'bathrooms', 'furnishing')
    def _check_land_details(self):
        for prop in self:
            if prop.category == 'land' and (prop.bedrooms or prop.bathrooms or prop.furnishing):
                raise ValidationError(self.env._(
                    "%(property)s is land: it cannot have bedrooms, bathrooms or a furnishing status.",
                    property=prop.display_name,
                ))

    @api.constrains('owner_id')
    def _check_owner_role(self):
        for prop in self:
            if prop.owner_id and not prop.owner_id.is_property_owner:
                raise ValidationError(self.env._(
                    "%(partner)s is not marked as a Property Owner.",
                    partner=prop.owner_id.display_name,
                ))

    @api.constrains('user_id')
    def _check_user_id(self):
        for prop in self:
            if prop.user_id and not prop.user_id.has_group('inom_rental_management.group_rental_agent'):
                raise ValidationError(self.env._(
                    "%(user)s cannot be the responsible agent: they are not a Real Estate user.",
                    user=prop.user_id.name,
                ))

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id:
            self.country_id = self.state_id.country_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                company = self.env['res.company'].browse(vals.get('company_id')) or self.env.company
                vals['code'] = self.env['ir.sequence'].with_company(company).next_by_code('property.property')
        return super().create(vals_list)

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self._check_can_archive()
        return super().write(vals)

    def _check_can_archive(self):
        running = self.env['property.rental.contract'].sudo().search_count([
            ('property_id', 'in', self.ids), ('state', '=', 'running'),
        ])
        booked = self.env['property.sale.contract'].sudo().search_count([
            ('property_id', 'in', self.ids), ('state', '=', 'booked'),
        ])
        if running or booked:
            raise UserError(self.env._(
                "You cannot archive a property that has a running rental contract or a booked sale. "
                "Close or cancel the contract first."
            ))

    def action_set_available(self):
        for prop in self.filtered(lambda p: p.state == 'draft'):
            missing = []
            if not prop.owner_id:
                missing.append(self.env._("an owner"))
            if prop.property_for == 'rent' and not prop.rent_price:
                missing.append(self.env._("a rental price"))
            if prop.property_for == 'sale' and not prop.sale_price:
                missing.append(self.env._("a sale price"))
            if missing:
                raise UserError(self.env._(
                    "%(property)s needs %(missing)s before it can be made available.",
                    property=prop.display_name, missing=", ".join(missing),
                ))
            prop.state = 'available'

    def action_set_draft(self):
        self.filtered(lambda p: p.state == 'available').state = 'draft'

    def action_view_rental_contracts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_rental_contract')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {'default_property_id': self.id}
        return action

    def action_view_sale_contracts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_sale_contract')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {'default_property_id': self.id}
        return action

    def action_open_enquiry_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("New Enquiry"),
            'res_model': 'property.enquiry.create',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_property_id': self.id},
        }

    def action_view_enquiries(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_enquiry_all')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = {
            'default_property_id': self.id,
            'default_property_for': self.property_for,
            'active_test': False,
        }
        return action

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Documents"),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
            'help': self.env._(
                "<p class='o_view_nocontent_smiling_face'>Upload a document</p>"
                "<p>Keep deeds, floor plans, certificates and other files with the property.</p>"
            ),
        }
