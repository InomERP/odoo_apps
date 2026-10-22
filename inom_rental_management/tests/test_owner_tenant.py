import base64
import importlib.util
from datetime import date
from os.path import dirname, join

from dateutil.relativedelta import relativedelta
from lxml import etree
from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

PDF = base64.b64encode(b'%PDF-1.4 test identity document')


@tagged('post_install', '-at_install')
class TestOwnerTenant(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(cls.env, 'p4_agent', groups='inom_rental_management.group_rental_agent')
        cls.agent_2 = new_test_user(cls.env, 'p4_agent_2', groups='inom_rental_management.group_rental_agent')
        cls.manager = new_test_user(cls.env, 'p4_manager', groups='inom_rental_management.group_rental_manager')
        cls.accountant = new_test_user(cls.env, 'p4_accountant', groups='inom_rental_management.group_rental_accountant')
        cls.internal_user = new_test_user(cls.env, 'p4_internal', groups='base.group_user')

        Partner = cls.env['res.partner']
        cls.owner = Partner.create({
            'name': 'Rajesh Mehta', 'is_property_owner': True, 'email': 'rajesh@example.com',
            'phone': '+91 98250 00001', 'street': 'CG Road', 'city': 'Ahmedabad',
        })
        cls.owner_company = Partner.create({'name': 'Horizon Estates LLP', 'is_company': True, 'is_property_owner': True})
        cls.owner_contact = Partner.create({'name': 'Anil (Horizon)', 'parent_id': cls.owner_company.id, 'is_tenant': True})
        cls.tenant = Partner.create({
            'name': 'Neha Kulkarni', 'is_tenant': True, 'email': 'neha@example.com', 'phone': '+91 98250 00002',
        })
        cls.buyer = Partner.create({'name': 'Karan Desai', 'is_property_buyer': True})
        cls.plain_contact = Partner.create({'name': 'Just a Contact'})

        cls.type_apartment = cls.env['property.type'].create({'name': 'Apartment P4', 'category': 'residential'})
        cls.flat = cls.env['property.property'].create({
            'name': 'Skyline B-402', 'type_id': cls.type_apartment.id, 'owner_id': cls.owner.id,
            'user_id': cls.agent.id, 'rent_price': 25000.0,
        })
        cls.shop = cls.env['property.property'].create({
            'name': 'Metro Retail Shop G-03', 'type_id': cls.type_apartment.id, 'owner_id': cls.owner_company.id,
            'property_for': 'sale', 'sale_price': 6000000.0,
        })

    def _lease(self, **kwargs):
        vals = {
            'property_id': self.flat.id, 'tenant_id': self.tenant.id,
            'date_start': date(2026, 7, 1), 'date_end': date(2027, 5, 31),
        }
        vals.update(kwargs)
        return self.env['property.rental.contract'].create(vals)

    def _document(self, partner, user=None, **kwargs):
        vals = {'name': 'Passport', 'partner_id': partner.id, 'document_type': 'identity', 'file': PDF,
                'file_name': 'passport.pdf'}
        vals.update(kwargs)
        Document = self.env['property.partner.document']
        return (Document.with_user(user) if user else Document).create(vals)

    # ------------------------------------------------------------------
    # Owners and tenants on standard contacts
    # ------------------------------------------------------------------
    def test_owner_and_tenant_are_contacts(self):
        self.assertEqual(self.owner._name, 'res.partner')
        self.assertEqual(self.owner.email, 'rajesh@example.com')
        self.assertEqual(self.owner.city, 'Ahmedabad')
        owners = self.env['res.partner'].search(safe_eval(self.env.ref('inom_rental_management.action_property_owner').domain))
        self.assertIn(self.owner, owners)
        self.assertNotIn(self.tenant, owners)
        tenants = self.env['res.partner'].search([('is_tenant', '=', True)])
        self.assertIn(self.tenant, tenants)

    def test_owner_properties_and_smart_buttons(self):
        self.assertEqual(self.owner.owned_property_ids, self.flat)
        self.assertEqual(self.owner.owned_property_count, 1)
        new_flat = self.flat.copy({'name': 'Skyline B-403'})
        self.owner.invalidate_recordset(['owned_property_ids', 'owned_property_count'])
        self.assertEqual(self.owner.owned_property_count, 2)
        action = self.owner.action_view_owned_properties()
        self.assertEqual(self.env['property.property'].search(action['domain']), self.flat | new_flat)

    def test_tenant_rental_history(self):
        old = self._lease(date_start=date(2025, 1, 1), date_end=date(2025, 12, 31))
        old.action_start()
        old.action_close()
        current = self._lease()
        current.action_start()

        self.assertEqual(self.tenant.tenant_contract_ids, old | current)
        self.assertEqual(self.tenant.rental_contract_count, 2)
        self.assertEqual(self.owner.owner_contract_ids, old | current)
        self.assertEqual(self.owner.rental_contract_count, 2)
        action = self.tenant.action_view_rental_contracts()
        self.assertEqual(self.env['property.rental.contract'].search(action['domain']), old | current)
        self.assertEqual(action['context'].get('default_tenant_id'), self.tenant.id)

        sale = self.env['property.sale.contract'].create({'property_id': self.shop.id, 'buyer_id': self.buyer.id})
        self.assertEqual(self.buyer.sale_contract_count, 1)
        self.assertEqual(self.owner_company.sale_contract_count, 1)
        self.assertEqual(self.env['property.sale.contract'].search(self.buyer.action_view_sale_contracts()['domain']), sale)

    # ------------------------------------------------------------------
    # Invalid and duplicate relationships
    # ------------------------------------------------------------------
    def test_owner_must_have_owner_role(self):
        with self.assertRaises(ValidationError):
            self.flat.owner_id = self.plain_contact
        with self.assertRaises(ValidationError):
            self.env['property.property'].create({
                'name': 'Unowned', 'type_id': self.type_apartment.id, 'owner_id': self.tenant.id,
            })

    def test_invalid_tenant_and_buyer(self):
        with self.assertRaises(ValidationError):
            self._lease(tenant_id=self.plain_contact.id)
        # The owner, or a contact of the owning company, cannot rent its own property.
        self.owner.is_tenant = True
        with self.assertRaises(ValidationError):
            self._lease(tenant_id=self.owner.id)
        shop_for_rent = self.shop.copy({'property_for': 'rent', 'rent_price': 1000.0})
        with self.assertRaises(ValidationError):
            self._lease(property_id=shop_for_rent.id, tenant_id=self.owner_contact.id)
        # A buyer must have the role and cannot already own the property.
        with self.assertRaises(ValidationError):
            self.env['property.sale.contract'].create({'property_id': self.shop.id, 'buyer_id': self.tenant.id})
        self.owner_company.is_property_buyer = True
        with self.assertRaises(ValidationError):
            self.env['property.sale.contract'].create({'property_id': self.shop.id, 'buyer_id': self.owner_company.id})

    def test_no_double_letting(self):
        first = self._lease()
        first.action_start()
        other_tenant = self.env['res.partner'].create({'name': 'Vikram Rao', 'is_tenant': True})
        overlapping = self._lease(tenant_id=other_tenant.id, date_start=date(2027, 1, 1), date_end=date(2027, 12, 31))
        with self.assertRaises(UserError):
            overlapping.action_start()
        self.assertEqual(overlapping.state, 'draft')
        later = self._lease(tenant_id=other_tenant.id, date_start=date(2027, 6, 1), date_end=date(2028, 5, 31))
        later.action_start()
        self.assertEqual(later.state, 'running')

    def test_role_cannot_be_removed_while_in_use(self):
        with self.assertRaises(ValidationError):
            self.owner.is_property_owner = False
        self._lease()
        with self.assertRaises(ValidationError):
            self.tenant.is_tenant = False
        unused = self.env['res.partner'].create({'name': 'Unused tenant', 'is_tenant': True})
        unused.is_tenant = False

    def test_duplicate_documents(self):
        self._document(self.tenant, document_number='P1234567')
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self._document(self.owner, document_number='P1234567')
            self.env.flush_all()
        # Same number under another document type is a different document.
        self._document(self.tenant, document_number='P1234567', document_type='tax', name='Tax ID')

    def test_document_validation(self):
        with self.assertRaises(ValidationError):
            self._document(self.tenant, issue_date=date(2026, 1, 1), expiry_date=date(2025, 1, 1))
        with self.assertRaises(ValidationError):
            self._document(self.plain_contact)

    def test_delete_protection(self):
        """ Contacts linked to a property or a contract cannot be deleted. """
        self._lease()
        for partner in (self.owner, self.tenant):
            with self.subTest(partner=partner.name):
                try:
                    with mute_logger('odoo.sql_db'), self.env.cr.savepoint():
                        partner.unlink()
                        self.env.flush_all()
                except (UserError, IntegrityError):
                    pass
                else:
                    self.fail(f"{partner.name} was deleted although it is linked to a property or contract")
        self.assertEqual(self.flat.owner_id, self.owner)

    # ------------------------------------------------------------------
    # Confidential documents
    # ------------------------------------------------------------------
    def test_document_access(self):
        doc = self._document(self.tenant, user=self.agent, document_number='ID-AGENT-1')
        Document = self.env['property.partner.document']

        # The uploading agent sees it; another agent does not.
        self.assertIn(doc, Document.with_user(self.agent).search([]))
        self.assertNotIn(doc, Document.with_user(self.agent_2).search([]))
        with self.assertRaises(AccessError):
            doc.with_user(self.agent_2).read(['document_number'])
        attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'property.partner.document'), ('res_id', '=', doc.id), ('res_field', '=', 'file'),
        ])
        self.assertTrue(attachment)
        with self.assertRaises(AccessError):
            attachment.with_user(self.agent_2).read(['datas'])

        # Once agent 2 handles a lease for that tenant, the tenant's documents open for them.
        self._lease(user_id=self.agent_2.id)
        self.assertIn(doc, Document.with_user(self.agent_2).search([]))
        # Managers see every document.
        self.assertIn(doc, Document.with_user(self.manager).search([]))
        # Accountants and other users have no access at all.
        for user in (self.accountant, self.internal_user):
            with self.subTest(user=user.login), self.assertRaises(AccessError):
                Document.with_user(user).search([])
            with self.subTest(user=user.login), self.assertRaises(AccessError):
                attachment.with_user(user).read(['datas'])

    def test_owner_documents_visible_to_property_agent(self):
        doc = self._document(self.owner, user=self.manager, name='Title deed', document_type='ownership')
        # agent is responsible for the owner's flat, agent_2 is not.
        self.assertIn(doc, self.env['property.partner.document'].with_user(self.agent).search([]))
        self.assertNotIn(doc, self.env['property.partner.document'].with_user(self.agent_2).search([]))

    def test_contact_form_hides_documents_from_unauthorised_users(self):
        def form_arch(user):
            return self.env['res.partner'].with_user(user).get_views([(False, 'form')])['views']['form']['arch']

        self.assertIn('action_view_real_estate_documents', form_arch(self.agent))
        self.assertNotIn('action_view_real_estate_documents', form_arch(self.accountant))
        self.assertIn('tenant_contract_ids', form_arch(self.accountant))
        self.assertNotIn('tenant_contract_ids', form_arch(self.internal_user))
        self.assertNotIn('real_estate_document', form_arch(self.internal_user))
        # Reading the protected fields is refused, not just hidden.
        with self.assertRaises(AccessError):
            self.tenant.with_user(self.internal_user).read(['real_estate_document_ids'])
        with self.assertRaises(AccessError):
            self.tenant.with_user(self.accountant).read(['real_estate_document_ids'])

    # ------------------------------------------------------------------
    # Identity requirement
    # ------------------------------------------------------------------
    def test_identity_required_to_start_lease(self):
        self.env.company.rental_require_tenant_identity = True
        lease = self._lease(user_id=self.agent.id)
        with self.assertRaises(UserError):
            lease.action_start()
        self._document(self.tenant, expiry_date=date(2026, 6, 30), issue_date=date(2016, 7, 1))
        with self.assertRaises(UserError):
            lease.action_start()  # expires before the lease starts
        self._document(self.tenant, name='Aadhaar', document_number='1234-5678-9012')
        lease.with_user(self.agent).action_start()
        self.assertEqual(lease.state, 'running')

    def test_identity_not_required_by_default(self):
        self.assertFalse(self.env.company.rental_require_tenant_identity)
        lease = self._lease()
        lease.action_start()
        self.assertEqual(lease.state, 'running')

    def test_settings_field(self):
        settings = self.env['res.config.settings'].create({'rental_require_tenant_identity': True})
        settings.execute()
        self.assertTrue(self.env.company.rental_require_tenant_identity)

    # ------------------------------------------------------------------
    # Search, filters and archiving
    # ------------------------------------------------------------------
    def test_partner_filters(self):
        lease = self._lease(user_id=self.agent.id)
        lease.action_start()
        lonely_owner = self.env['res.partner'].create({'name': 'Owner without property', 'is_property_owner': True})
        arch = self.env['res.partner'].with_user(self.agent).get_views([(False, 'search')])['views']['search']['arch']
        domains = {node.get('name'): safe_eval(node.get('domain')) for node in etree.fromstring(arch).iter('filter')
                   if node.get('name') in ('property_owners', 'tenants', 'property_buyers', 'current_tenants',
                                           'owners_without_property')}
        Partner = self.env['res.partner'].with_user(self.agent)
        self.assertIn(self.tenant, Partner.search(domains['current_tenants']))
        self.assertNotIn(self.owner_contact, Partner.search(domains['current_tenants']))
        self.assertIn(lonely_owner, Partner.search(domains['owners_without_property']))
        self.assertNotIn(self.owner, Partner.search(domains['owners_without_property']))
        self.assertIn(self.buyer, Partner.search(domains['property_buyers']))

    def test_document_filters(self):
        today = fields.Date.context_today(self.env.user)
        expired = self._document(self.tenant, name='Old ID', issue_date=today - relativedelta(years=10),
                                 expiry_date=today - relativedelta(days=1))
        soon = self._document(self.tenant, name='Soon', expiry_date=today + relativedelta(days=10))
        later = self._document(self.tenant, name='Later', expiry_date=today + relativedelta(years=2))
        self.assertTrue(expired.is_expired)
        self.assertFalse(soon.is_expired)
        Document = self.env['property.partner.document'].with_user(self.manager)
        arch = Document.get_views([(False, 'search')])['views']['search']['arch']
        eval_context = {'context_today': lambda: today, 'relativedelta': relativedelta}
        domains = {node.get('name'): safe_eval(node.get('domain'), eval_context)
                   for node in etree.fromstring(arch).iter('filter') if node.get('domain')}
        self.assertEqual(Document.search(domains['expired']) & (expired | soon | later), expired)
        self.assertEqual(Document.search(domains['expiring_soon']) & (expired | soon | later), soon)
        self.assertIn(later, Document.search(domains['identity']))
        self.assertIn(later, Document.search(domains['tenants']))

    def test_archiving(self):
        with self.assertRaises(UserError):
            self.owner.action_archive()
        lease = self._lease()
        lease.action_start()
        with self.assertRaises(UserError):
            self.tenant.action_archive()
        lease.action_close()
        self.tenant.action_archive()
        self.assertFalse(self.tenant.active)
        self.assertNotIn(self.tenant, self.env['res.partner'].search([('is_tenant', '=', True)]))
        self.tenant.action_unarchive()
        # An owner can be archived once their properties are archived.
        self.flat.action_archive()
        self.owner.action_archive()
        self.assertFalse(self.owner.active)

    # ------------------------------------------------------------------
    # Upgrade
    # ------------------------------------------------------------------
    def test_migration_restores_roles(self):
        lease = self._lease()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET is_property_owner = FALSE, is_tenant = FALSE WHERE id IN %s",
            [(self.owner.id, self.tenant.id)],
        )
        path = join(dirname(dirname(__file__)), 'migrations', '19.0.1.2.0', 'post-migrate.py')
        spec = importlib.util.spec_from_file_location('rental_management_post_migrate_1_2', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, '19.0.1.1.0')
        self.env.invalidate_all()
        self.assertTrue(self.owner.is_property_owner)
        self.assertTrue(self.tenant.is_tenant)
        self.assertEqual(lease.tenant_id, self.tenant)
