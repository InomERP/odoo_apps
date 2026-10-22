from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools.safe_eval import safe_eval


@tagged('post_install', '-at_install')
class TestEnquiry(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        agent_and_sales = 'inom_rental_management.group_rental_agent,sales_team.group_sale_salesman'
        cls.sales_agent = new_test_user(cls.env, 'p8_sales_agent', groups=agent_and_sales)
        cls.sales_agent_2 = new_test_user(cls.env, 'p8_sales_agent_2', groups=agent_and_sales)
        cls.plain_agent = new_test_user(cls.env, 'p8_plain_agent', groups='inom_rental_management.group_rental_agent')
        cls.salesman_only = new_test_user(cls.env, 'p8_salesman_only', groups='sales_team.group_sale_salesman')

        cls.property_type = cls.env['property.type'].create({'name': 'Apartment P8', 'category': 'residential'})
        cls.owner = cls.env['res.partner'].create({'name': 'P8 Owner', 'is_property_owner': True})
        cls.customer = cls.env['res.partner'].create({'name': 'P8 Customer', 'email': 'customer@example.com'})
        cls.flat = cls.env['property.property'].create({
            'name': 'Skyline E-501', 'type_id': cls.property_type.id, 'owner_id': cls.owner.id,
            'property_for': 'rent', 'rent_price': 18000.0, 'user_id': cls.sales_agent.id,
        })
        cls.villa = cls.env['property.property'].create({
            'name': 'Green Meadows Villa 20', 'type_id': cls.property_type.id, 'owner_id': cls.owner.id,
            'property_for': 'sale', 'sale_price': 7500000.0, 'user_id': cls.sales_agent.id,
        })
        (cls.flat | cls.villa).action_set_available()

    def _enquire(self, prop, user=None, **kwargs):
        Wizard = self.env['property.enquiry.create'].with_user(user or self.sales_agent)
        wizard = Wizard.create({'property_id': prop.id, **kwargs})
        action = wizard.action_create()
        return self.env['crm.lead'].browse(action['res_id'])

    # ------------------------------------------------------------------
    # Creating enquiries
    # ------------------------------------------------------------------
    def test_sale_enquiry(self):
        lead = self._enquire(self.villa, partner_id=self.customer.id, ask_price=7000000.0)
        self.assertEqual(lead.type, 'opportunity')
        self.assertEqual(lead.property_id, self.villa)
        self.assertEqual(lead.property_for, 'sale')
        self.assertEqual(lead.partner_id, self.customer)
        self.assertEqual(lead.ask_price, 7000000.0)
        self.assertEqual(lead.listed_price, 7500000.0)
        self.assertEqual(lead.user_id, self.sales_agent, "The property's agent is responsible")
        self.assertEqual(lead.property_enquiry_state, 'open')
        # A follow-up is scheduled for the responsible agent.
        activity = lead.activity_ids
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, self.sales_agent)
        self.assertEqual(activity.date_deadline, fields.Date.context_today(lead) + timedelta(days=1))
        # An enquiry is not a sale.
        self.assertEqual(self.villa.state, 'available')
        self.assertFalse(self.villa.sale_contract_ids)

    def test_rental_enquiry_from_prospect(self):
        lead = self._enquire(self.flat, contact_name='Riya Shah', email_from='riya@example.com', phone='+91 90000 00001')
        self.assertEqual(lead.property_for, 'rent')
        self.assertFalse(lead.partner_id, "A prospect stays a prospect until a contract is drafted")
        self.assertEqual(lead.contact_name, 'Riya Shah')
        self.assertEqual(lead.email_from, 'riya@example.com')
        self.assertEqual(self.flat.state, 'available')
        self.assertFalse(self.flat.rental_contract_ids)

    def test_enquiry_created_in_crm(self):
        # A salesperson who sees all leads may assign the enquiry to the property's agent.
        self.sales_agent_2.group_ids += self.env.ref('sales_team.group_sale_salesman_all_leads')
        lead = self.env['crm.lead'].with_user(self.sales_agent_2).create({
            'name': 'Walk-in for E-501', 'type': 'opportunity', 'partner_id': self.customer.id,
            'property_for': 'rent', 'property_id': self.flat.id,
        })
        self.assertEqual(lead.user_id, self.sales_agent, "Defaults to the property's agent")
        self.assertEqual(len(lead.activity_ids), 1)
        # A salesperson limited to their own leads keeps the enquiry, so they do not lose sight of it.
        own = self.env['crm.lead'].with_user(self.salesman_only).create({
            'name': 'Own docs', 'type': 'opportunity', 'property_for': 'rent', 'property_id': self.flat.id,
        })
        self.assertEqual(own.user_id, self.salesman_only)

        self.env.company.rental_enquiry_followup_days = 0
        quiet = self.env['crm.lead'].create({
            'name': 'No follow-up', 'property_for': 'rent', 'property_id': self.flat.id,
            'partner_id': self.customer.id,
        })
        self.assertFalse(quiet.activity_ids)
        plain_lead = self.env['crm.lead'].create({'name': 'Not about a property'})
        self.assertFalse(plain_lead.property_enquiry_state)
        self.assertFalse(plain_lead.activity_ids, "Other CRM leads are untouched")

    def test_wizard_requires_a_customer_or_prospect(self):
        with self.assertRaises(UserError):
            self._enquire(self.flat)

    # ------------------------------------------------------------------
    # Duplicates
    # ------------------------------------------------------------------
    def test_duplicate_enquiries(self):
        first = self._enquire(self.flat, partner_id=self.customer.id)
        wizard = self.env['property.enquiry.create'].with_user(self.sales_agent_2).create({
            'property_id': self.flat.id, 'partner_id': self.customer.id,
        })
        self.assertEqual(wizard.duplicate_count, 1, "Found even when handled by another salesperson")
        self.assertIn(first.name, wizard.duplicate_summary)
        self.assertIn(self.sales_agent.name, wizard.duplicate_summary)
        self.assertEqual(wizard.user_id, self.sales_agent_2, "An own-documents salesperson keeps the enquiry")
        with self.assertRaises(UserError):
            wizard.action_create()
        with self.assertRaises(UserError):
            wizard.action_open_existing()  # handled by a colleague this user cannot see
        self.assertEqual(
            self.env['property.enquiry.create'].with_user(self.sales_agent).create({
                'property_id': self.flat.id, 'partner_id': self.customer.id,
            }).action_open_existing()['res_id'], first.id,
        )
        wizard.create_anyway = True
        second = self.env['crm.lead'].browse(wizard.action_create()['res_id'])
        self.assertNotEqual(second, first)
        self.assertEqual(second.user_id, self.sales_agent_2)
        self.assertEqual(second.with_user(self.sales_agent_2).property_duplicate_count, 1)

        # Same customer, other property or other purpose: not a duplicate.
        self._enquire(self.villa, partner_id=self.customer.id)
        # A contact of the same company counts as the same customer.
        colleague = self.env['res.partner'].create({'name': 'Colleague', 'parent_id': self.customer.id})
        self.customer.is_company = True
        with self.assertRaises(UserError):
            self._enquire(self.flat, partner_id=colleague.id)

    def test_duplicate_by_email_and_closed_enquiries(self):
        first = self._enquire(self.flat, contact_name='Riya', email_from='Riya@Example.com')
        with self.assertRaises(UserError):
            self._enquire(self.flat, contact_name='Riya S.', email_from='riya@example.com')
        first.action_set_lost()
        again = self._enquire(self.flat, contact_name='Riya S.', email_from='riya@example.com')
        self.assertTrue(again, "A lost enquiry does not block a new one")

    # ------------------------------------------------------------------
    # Conversion workflow
    # ------------------------------------------------------------------
    def test_convert_rental_enquiry(self):
        lead = self._enquire(self.flat, contact_name='Riya Shah', email_from='riya@example.com')
        action = lead.with_user(self.sales_agent).action_create_property_rental()
        lease = self.env['property.rental.contract'].browse(action['res_id'])
        self.assertEqual(lease.state, 'draft')
        self.assertEqual(lease.lead_id, lead)
        self.assertEqual(lease.property_id, self.flat)
        self.assertTrue(lead.partner_id, "The prospect became a customer through standard CRM")
        self.assertEqual(lease.tenant_id, lead.partner_id)
        self.assertTrue(lease.tenant_id.is_tenant)
        self.assertEqual(lead.property_enquiry_state, 'contract')
        self.assertEqual(lead.won_status, 'pending', "Drafting a lease does not win the enquiry")
        self.assertEqual(self.flat.state, 'available')
        with self.assertRaises(UserError):
            lead.action_create_property_rental()  # one live contract per enquiry

        lease.with_user(self.sales_agent).action_start()
        self.assertEqual(lead.won_status, 'won', "Starting the lease wins the enquiry")
        self.assertEqual(lead.property_enquiry_state, 'won')
        self.assertEqual(lead.with_user(self.sales_agent).property_rental_contract_count, 1)

    def test_cancelled_contract_reopens_enquiry(self):
        lead = self._enquire(self.flat, partner_id=self.customer.id)
        lease = self.env['property.rental.contract'].browse(lead.action_create_property_rental()['res_id'])
        self.assertEqual(lead.property_enquiry_state, 'contract')
        lease.action_cancel()
        self.assertEqual(lead.property_enquiry_state, 'open')
        lead.action_create_property_rental()  # allowed again
        self.assertEqual(len(lead.property_rental_contract_ids), 2)

    def test_convert_sale_enquiry(self):
        lead = self._enquire(self.villa, partner_id=self.customer.id)
        sale = self.env['property.sale.contract'].browse(lead.action_create_property_sale()['res_id'])
        self.assertEqual((sale.state, sale.lead_id, sale.buyer_id), ('draft', lead, self.customer))
        self.assertTrue(self.customer.is_property_buyer)
        self.assertEqual(lead.property_enquiry_state, 'contract')
        with self.assertRaises(UserError):
            lead.action_create_property_sale()

    def test_conversion_matches_purpose(self):
        rent_lead = self._enquire(self.flat, partner_id=self.customer.id)
        with self.assertRaises(UserError):
            rent_lead.action_create_property_sale()
        sale_lead = self._enquire(self.villa, partner_id=self.customer.id)
        with self.assertRaises(UserError):
            sale_lead.action_create_property_rental()

    def test_lost_enquiry(self):
        lead = self._enquire(self.flat, partner_id=self.customer.id)
        lead.action_set_lost()
        self.assertEqual(lead.property_enquiry_state, 'lost')

    # ------------------------------------------------------------------
    # Links and history
    # ------------------------------------------------------------------
    def test_links_and_history(self):
        rent_lead = self._enquire(self.flat, partner_id=self.customer.id)
        lost = self._enquire(self.flat, contact_name='Someone', email_from='someone@example.com')
        lost.action_set_lost()
        sale_lead = self._enquire(self.villa, partner_id=self.customer.id)

        Property = self.env['property.property'].with_user(self.sales_agent)
        self.assertEqual(Property.browse(self.flat.id).lead_count, 2, "Lost enquiries stay in the history")
        action = self.flat.with_user(self.sales_agent).action_view_enquiries()
        found = self.env['crm.lead'].with_context(active_test=False).search(action['domain'])
        self.assertEqual(found, rent_lead | lost)
        self.assertEqual(self.villa.lead_ids, sale_lead)
        # The customer's standard CRM opportunities include their property enquiries.
        self.assertIn(rent_lead, self.env['crm.lead'].search([('partner_id', '=', self.customer.id)]))
        self.assertEqual(self.customer.opportunity_count, 2)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------
    def test_access_restrictions(self):
        lead = self._enquire(self.flat, partner_id=self.customer.id)
        # Real Estate agents without CRM access cannot see or record enquiries.
        with self.assertRaises(AccessError):
            self.env['crm.lead'].with_user(self.plain_agent).search([])
        with self.assertRaises(AccessError):
            self.env['property.enquiry.create'].with_user(self.plain_agent).create({
                'property_id': self.flat.id, 'partner_id': self.customer.id,
            })
        arch = self.env['property.property'].with_user(self.plain_agent).get_views([(False, 'form')])['views']['form']['arch']
        self.assertNotIn('action_open_enquiry_wizard', arch)
        self.assertNotIn('action_view_enquiries', arch)

        # CRM users without a Real Estate role do not see the property details of leads.
        arch = self.env['crm.lead'].with_user(self.salesman_only).get_views([(False, 'form')])['views']['form']['arch']
        self.assertNotIn('rental_management_property', arch)
        self.assertNotIn('action_create_property_rental', arch)
        with self.assertRaises(AccessError):
            lead.with_user(self.salesman_only).read(['property_rental_contract_ids'])

        # Standard CRM record rules still apply: "own documents only" salespeople see their own leads.
        self.env.ref('sales_team.group_sale_salesman_all_leads').user_ids -= self.sales_agent_2
        own_rule_users = self.sales_agent_2.has_group('sales_team.group_sale_salesman_all_leads')
        if not own_rule_users:
            self.assertNotIn(lead, self.env['crm.lead'].with_user(self.sales_agent_2).search([]))
            self.assertEqual(self.flat.with_user(self.sales_agent_2).lead_count, 0)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def test_filters_and_report(self):
        rent = self._enquire(self.flat, partner_id=self.customer.id)
        sale = self._enquire(self.villa, partner_id=self.customer.id)
        sale.action_create_property_sale()
        Lead = self.env['crm.lead'].with_user(self.sales_agent)
        arch = Lead.get_views([(False, 'search')])['views']['search']['arch']
        for name, expected in (
            ('rent_enquiries', rent), ('sale_enquiries', sale), ('enquiry_open', rent), ('enquiry_contract', sale),
        ):
            domain = safe_eval(next(
                node.get('domain') for node in self._filters(arch) if node.get('name') == name
            ))
            with self.subTest(filter=name):
                self.assertEqual(Lead.search(domain) & (rent | sale), expected)

        report = self.env.ref('inom_rental_management.action_property_enquiry_analysis')
        groups = Lead.formatted_read_group(safe_eval(report.domain), ['property_id', 'property_enquiry_state'], ['__count'])
        counts = {(g['property_id'][0], g['property_enquiry_state']): g['__count'] for g in groups}
        self.assertEqual(counts[(self.flat.id, 'open')], 1)
        self.assertEqual(counts[(self.villa.id, 'contract')], 1)

    @staticmethod
    def _filters(arch):
        from lxml import etree
        return etree.fromstring(arch).iter('filter')
