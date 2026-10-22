from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

REAL_ESTATE_USERS = 'inom_rental_management.group_rental_agent,inom_rental_management.group_rental_accountant'
SALESMAN_GROUP = 'sales_team.group_sale_salesman'


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    property_id = fields.Many2one(
        'property.property', string='Property', index='btree_not_null', check_company=True,
        domain="[('state', 'not in', ('sold',)), ('property_for', '=?', property_for)]",
    )
    property_for = fields.Selection(
        selection=[('rent', 'Rent'), ('sale', 'Sale')], string='Enquiry For', index='btree_not_null',
    )
    ask_price = fields.Monetary(
        string='Asking Price', currency_field='company_currency',
        help="Price the customer asks for or offers, compared with the listed price of the property.",
    )
    listed_price = fields.Monetary(
        compute='_compute_listed_price', currency_field='company_currency', compute_sudo=True,
    )
    property_sale_contract_ids = fields.One2many(
        'property.sale.contract', 'lead_id', string='Property Sales', groups=REAL_ESTATE_USERS,
    )
    property_sale_contract_count = fields.Integer(
        compute='_compute_property_contract_counts', groups=REAL_ESTATE_USERS,
    )
    property_rental_contract_ids = fields.One2many(
        'property.rental.contract', 'lead_id', string='Rental Contracts', groups=REAL_ESTATE_USERS,
    )
    property_rental_contract_count = fields.Integer(
        compute='_compute_property_contract_counts', groups=REAL_ESTATE_USERS,
    )
    property_enquiry_state = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('contract', 'Contract Drafted'),
            ('won', 'Won'),
            ('lost', 'Lost'),
        ],
        string='Enquiry Status', compute='_compute_property_enquiry_state', store=True, compute_sudo=True,
        help="Open: being worked on. Contract Drafted: a sale or lease was created from it but is not yet "
             "sold or started. Won and Lost follow the CRM outcome.",
    )
    property_duplicate_count = fields.Integer(compute='_compute_property_duplicates')
    property_duplicate_summary = fields.Text(
        string='Similar Open Enquiries', compute='_compute_property_duplicates',
        help="Other open enquiries of this customer for the same property, including ones you cannot open.",
    )

    def _compute_listed_price(self):
        for lead in self:
            prop = lead.property_id
            lead.listed_price = prop.sale_price if (lead.property_for or prop.property_for) == 'sale' else prop.rent_price

    def _compute_property_contract_counts(self):
        for lead in self:
            lead.property_sale_contract_count = len(lead.property_sale_contract_ids)
            lead.property_rental_contract_count = len(lead.property_rental_contract_ids)

    @api.depends(
        'property_for', 'won_status', 'property_sale_contract_ids.state', 'property_rental_contract_ids.state',
    )
    def _compute_property_enquiry_state(self):
        for lead in self:
            if not lead.property_for:
                lead.property_enquiry_state = False
            elif lead.won_status == 'won':
                lead.property_enquiry_state = 'won'
            elif lead.won_status == 'lost':
                lead.property_enquiry_state = 'lost'
            elif lead.property_sale_contract_ids.filtered(lambda c: c.state != 'cancelled') \
                    or lead.property_rental_contract_ids.filtered(lambda c: c.state != 'cancelled'):
                lead.property_enquiry_state = 'contract'
            else:
                lead.property_enquiry_state = 'open'

    @api.depends('property_id', 'property_for', 'partner_id', 'email_from')
    def _compute_property_duplicates(self):
        for lead in self:
            duplicates = lead._find_open_property_enquiries(
                lead.property_id, lead.property_for, lead.partner_id, lead.email_from,
            ) - lead._origin.sudo()
            lead.property_duplicate_count = len(duplicates)
            lead.property_duplicate_summary = duplicates._property_enquiry_summary()

    def _property_enquiry_summary(self):
        """ One line per enquiry, safe to show to users who cannot open it. """
        return "\n".join(
            self.env._("%(lead)s, handled by %(user)s, received %(date)s",
                       lead=lead.name, user=lead.user_id.name or self.env._("nobody"),
                       date=fields.Date.to_string(lead.create_date.date()) if lead.create_date else "")
            for lead in self.sudo()
        )

    @api.model
    def _default_property_agent(self, prop):
        """ The property's agent, when they are a salesperson and the current user may assign
        the enquiry to them without losing sight of it (CRM "own documents" rule). """
        agent = prop.sudo().user_id
        user = self.env.user
        if not agent or not agent.has_group(SALESMAN_GROUP):
            return self.env['res.users']
        if agent == user or user.has_group('sales_team.group_sale_salesman_all_leads') or self.env.su:
            return agent
        return self.env['res.users']

    @api.model
    def _find_open_property_enquiries(self, prop, property_for, partner=False, email=False):
        """ Open enquiries of the same customer (or email) for the same property and purpose.
        Searched across all salespeople, so a duplicate handled by a colleague is found too. """
        if not prop or not property_for or not (partner or email):
            return self.browse()
        customer = []
        if partner:
            customer = [('partner_id', 'child_of', partner.commercial_partner_id.id)]
        if email:
            email_domain = [('email_normalized', '=', email.strip().lower())]
            customer = ['|'] + customer + email_domain if customer else email_domain
        return self.sudo().search([
            ('property_id', '=', prop.id),
            ('property_for', '=', property_for),
            ('won_status', '=', 'pending'),
        ] + customer)

    # ------------------------------------------------------------------
    # Responsible agent and follow-up
    # ------------------------------------------------------------------
    @api.onchange('property_id')
    def _onchange_property_id_rental(self):
        prop = self.property_id
        if prop:
            if not self.property_for:
                self.property_for = prop.property_for
            agent = self._default_property_agent(prop)
            if agent and not self._origin.user_id:
                self.user_id = agent

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('property_id') and not vals.get('user_id'):
                agent = self._default_property_agent(self.env['property.property'].browse(vals['property_id']))
                if agent:
                    vals['user_id'] = agent.id
        leads = super().create(vals_list)
        leads.filtered('property_for')._schedule_property_followup()
        return leads

    def _schedule_property_followup(self):
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        for lead in self:
            days = (lead.company_id or self.env.company).rental_enquiry_followup_days
            if days <= 0 or not lead.active:
                continue
            lead.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.context_today(lead) + relativedelta(days=days),
                summary=self.env._("Follow up property enquiry"),
                user_id=lead.user_id.id or self.env.user.id,
            )

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------
    def _ensure_property_customer(self):
        """ Use the enquiry's customer, or create one from the prospect's details with standard CRM. """
        self.ensure_one()
        if not self.partner_id:
            if not (self.contact_name or self.partner_name or self.email_from):
                raise UserError(self.env._("Set the customer on the enquiry before creating a contract."))
            self._handle_partner_assignment(create_missing=True)
        return self.partner_id

    def _check_no_open_contract(self, contracts):
        open_contracts = contracts.filtered(lambda c: c.state != 'cancelled')
        if open_contracts:
            raise UserError(self.env._(
                "This enquiry already led to %(contract)s. Open it from the enquiry instead of creating another.",
                contract=", ".join(open_contracts.mapped('name')),
            ))

    def action_create_property_sale(self):
        """ Turn a sale enquiry into a draft sale. The enquiry stays open: only a sold sale wins it. """
        self.ensure_one()
        if self.property_for != 'sale' or not self.property_id:
            raise UserError(self.env._("Set the enquiry to Sale and choose the property first."))
        self._check_no_open_contract(self.property_sale_contract_ids)
        buyer = self._ensure_property_customer()
        if not buyer.is_property_buyer:
            buyer.is_property_buyer = True
        contract = self.env['property.sale.contract'].create({
            'property_id': self.property_id.id,
            'buyer_id': buyer.id,
            'lead_id': self.id,
            'user_id': self.env.user.id,
            'company_id': (self.company_id or self.property_id.company_id).id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'property.sale.contract',
            'view_mode': 'form',
            'res_id': contract.id,
        }

    def action_create_property_rental(self):
        """ Turn a rental enquiry into a draft lease. The enquiry stays open: only a started lease wins it. """
        self.ensure_one()
        if self.property_for != 'rent' or not self.property_id:
            raise UserError(self.env._("Set the enquiry to Rent and choose the property first."))
        self._check_no_open_contract(self.property_rental_contract_ids)
        tenant = self._ensure_property_customer()
        if not tenant.is_tenant:
            tenant.is_tenant = True
        today = fields.Date.context_today(self)
        contract = self.env['property.rental.contract'].create({
            'property_id': self.property_id.id,
            'tenant_id': tenant.id,
            'lead_id': self.id,
            'user_id': self.env.user.id,
            'company_id': (self.company_id or self.property_id.company_id).id,
            'date_start': today,
            'date_end': today + relativedelta(years=1, days=-1),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'property.rental.contract',
            'view_mode': 'form',
            'res_id': contract.id,
        }

    def action_view_property_sales(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_sale_contract')
        action['domain'] = [('lead_id', '=', self.id)]
        return action

    def action_view_property_rentals(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('inom_rental_management.action_property_rental_contract')
        action['domain'] = [('lead_id', '=', self.id)]
        return action
