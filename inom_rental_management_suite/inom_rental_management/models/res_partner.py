from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

REAL_ESTATE_USERS = 'inom_rental_management.group_rental_agent,inom_rental_management.group_rental_accountant'
REAL_ESTATE_AGENTS = 'inom_rental_management.group_rental_agent'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_property_owner = fields.Boolean(string='Property Owner')
    is_tenant = fields.Boolean(string='Tenant')
    is_property_buyer = fields.Boolean(string='Property Buyer')
    owned_property_ids = fields.One2many('property.property', 'owner_id', string='Owned Properties')
    owned_property_count = fields.Integer(compute='_compute_owned_property_count', groups=REAL_ESTATE_USERS)

    tenant_contract_ids = fields.One2many(
        'property.rental.contract', 'tenant_id', string='Rental History', groups=REAL_ESTATE_USERS,
    )
    owner_contract_ids = fields.One2many(
        'property.rental.contract', 'owner_id', string='Leases on Owned Properties', groups=REAL_ESTATE_USERS,
    )
    buyer_contract_ids = fields.One2many(
        'property.sale.contract', 'buyer_id', string='Purchases', groups=REAL_ESTATE_USERS,
    )
    rental_contract_count = fields.Integer(compute='_compute_real_estate_contract_counts', groups=REAL_ESTATE_USERS)
    sale_contract_count = fields.Integer(compute='_compute_real_estate_contract_counts', groups=REAL_ESTATE_USERS)
    real_estate_document_ids = fields.One2many(
        'property.partner.document', 'partner_id', string='Real Estate Documents', groups=REAL_ESTATE_AGENTS,
    )
    real_estate_document_count = fields.Integer(compute='_compute_real_estate_document_count', groups=REAL_ESTATE_AGENTS)

    @api.depends('owned_property_ids')
    def _compute_owned_property_count(self):
        counts = dict(self.env['property.property']._read_group(
            [('owner_id', 'in', self.ids)], groupby=['owner_id'], aggregates=['__count'],
        ))
        for partner in self:
            partner.owned_property_count = counts.get(partner, 0)

    def _compute_real_estate_contract_counts(self):
        Rental = self.env['property.rental.contract']
        Sale = self.env['property.sale.contract']
        for partner in self:
            partner.rental_contract_count = Rental.search_count(partner._rental_contract_domain())
            partner.sale_contract_count = Sale.search_count(partner._sale_contract_domain())

    def _compute_real_estate_document_count(self):
        counts = dict(self.env['property.partner.document']._read_group(
            [('partner_id', 'in', self.ids)], groupby=['partner_id'], aggregates=['__count'],
        ))
        for partner in self:
            partner.real_estate_document_count = counts.get(partner, 0)

    def _rental_contract_domain(self):
        return ['|', ('tenant_id', '=', self.id), ('owner_id', '=', self.id)]

    def _sale_contract_domain(self):
        return ['|', ('buyer_id', '=', self.id), ('owner_id', '=', self.id)]

    @api.constrains('is_property_owner', 'is_tenant', 'is_property_buyer')
    def _check_real_estate_roles(self):
        """ A role cannot be removed while records still depend on it. """
        Property = self.env['property.property'].sudo().with_context(active_test=False)
        Rental = self.env['property.rental.contract'].sudo()
        Sale = self.env['property.sale.contract'].sudo()
        for partner in self:
            if not partner.is_property_owner and Property.search_count([('owner_id', '=', partner.id)], limit=1):
                raise ValidationError(self.env._(
                    "%(partner)s still owns properties: reassign them before removing the Property Owner role.",
                    partner=partner.display_name,
                ))
            if not partner.is_tenant and Rental.search_count([('tenant_id', '=', partner.id)], limit=1):
                raise ValidationError(self.env._(
                    "%(partner)s has rental contracts: the Tenant role cannot be removed.",
                    partner=partner.display_name,
                ))
            if not partner.is_property_buyer and Sale.search_count([('buyer_id', '=', partner.id)], limit=1):
                raise ValidationError(self.env._(
                    "%(partner)s has sale contracts: the Property Buyer role cannot be removed.",
                    partner=partner.display_name,
                ))

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self._check_can_archive_real_estate()
        return super().write(vals)

    def _check_can_archive_real_estate(self):
        Property = self.env['property.property'].sudo()
        Rental = self.env['property.rental.contract'].sudo()
        Sale = self.env['property.sale.contract'].sudo()
        for partner in self.filtered(lambda p: p.is_property_owner or p.is_tenant or p.is_property_buyer):
            if Property.search_count([('owner_id', '=', partner.id)], limit=1):
                raise UserError(self.env._(
                    "%(partner)s still owns active properties: reassign or archive them first.",
                    partner=partner.display_name,
                ))
            if Rental.search_count([('tenant_id', '=', partner.id), ('state', '=', 'running')], limit=1):
                raise UserError(self.env._(
                    "%(partner)s has a running rental contract: close it first.",
                    partner=partner.display_name,
                ))
            if Sale.search_count([('buyer_id', '=', partner.id), ('state', '=', 'booked')], limit=1):
                raise UserError(self.env._(
                    "%(partner)s has a booked property sale: complete or cancel it first.",
                    partner=partner.display_name,
                ))

    def _has_valid_identity_document(self, on_date):
        self.ensure_one()
        partners = self.commercial_partner_id | self
        return bool(self.env['property.partner.document'].sudo().search_count([
            ('partner_id', 'in', partners.ids),
            ('document_type', '=', 'identity'),
            '|', ('expiry_date', '=', False), ('expiry_date', '>=', on_date),
        ], limit=1))

    def action_view_owned_properties(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_property')
        action['domain'] = [('owner_id', '=', self.id)]
        action['context'] = {'default_owner_id': self.id}
        return action

    def action_view_rental_contracts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_rental_contract')
        action['domain'] = self._rental_contract_domain()
        action['context'] = {'default_tenant_id': self.id} if self.is_tenant else {}
        return action

    def action_view_sale_contracts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_sale_contract')
        action['domain'] = self._sale_contract_domain()
        action['context'] = {'default_buyer_id': self.id} if self.is_property_buyer else {}
        return action

    def action_view_real_estate_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_partner_document')
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action
