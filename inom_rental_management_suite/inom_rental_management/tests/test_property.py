import base64
from datetime import date

from lxml import etree
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

# 1x1 transparent PNG
PNG = base64.b64encode(bytes.fromhex(
    '89504e470d0a1a0a0000000d4948445200000001000000010806000000'
    '1f15c4890000000d4944415478da63f8ffff3f0005fe02fea7d65e9f0000000049454e44ae426082'
))


@tagged('post_install', '-at_install')
class TestProperty(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Real Estate Company B'})

        cls.agent = new_test_user(cls.env, 'p3_agent', groups='inom_rental_management.group_rental_agent')
        cls.manager = new_test_user(cls.env, 'p3_manager', groups='inom_rental_management.group_rental_manager')
        cls.accountant = new_test_user(cls.env, 'p3_accountant', groups='inom_rental_management.group_rental_accountant')
        cls.internal_user = new_test_user(cls.env, 'p3_internal', groups='base.group_user')
        cls.agent_b = new_test_user(
            cls.env, 'p3_agent_b', groups='inom_rental_management.group_rental_agent',
            company_id=cls.company_b.id, company_ids=[cls.company_b.id],
        )

        cls.type_apartment = cls.env['property.type'].create({'name': 'Apartment P3', 'category': 'residential'})
        cls.type_office = cls.env['property.type'].create({'name': 'Office P3', 'category': 'commercial'})
        cls.type_warehouse = cls.env['property.type'].create({'name': 'Warehouse P3', 'category': 'industrial'})
        cls.type_plot = cls.env['property.type'].create({'name': 'Plot P3', 'category': 'land'})
        cls.owner = cls.env['res.partner'].create({'name': 'Horizon Estates LLP', 'is_property_owner': True})
        cls.owner_b = cls.env['res.partner'].create({
            'name': 'Company B Owner', 'is_property_owner': True, 'company_id': cls.company_b.id,
        })
        cls.tenant = cls.env['res.partner'].create({'name': 'P3 Tenant', 'is_tenant': True})

        cls.apartment = cls.env['property.property'].create({
            'name': 'Skyline A-205',
            'type_id': cls.type_apartment.id,
            'property_for': 'rent',
            'owner_id': cls.owner.id,
            'user_id': cls.agent.id,
            'street': 'Sardar Patel Ring Road',
            'city': 'Ahmedabad',
            'zip': '380059',
            'country_id': cls.env.ref('base.in').id,
            'bedrooms': 3,
            'bathrooms': 2,
            'furnishing': 'semi_furnished',
            'total_area': 1620.0,
            'rent_price': 32000.0,
        })
        cls.office = cls.env['property.property'].create({
            'name': 'Metro Office Suite 501',
            'type_id': cls.type_office.id,
            'property_for': 'sale',
            'owner_id': cls.owner.id,
            'total_area': 2400.0,
            'sale_price': 15000000.0,
        })
        cls.plot = cls.env['property.property'].create({
            'name': 'Land Parcel NH-52',
            'type_id': cls.type_plot.id,
            'property_for': 'sale',
            'land_area': 4500.0,
            'area_unit': 'sq_yd',
            'sale_price': 8000000.0,
        })

    # ------------------------------------------------------------------
    # Creation and categories
    # ------------------------------------------------------------------
    def test_create_properties_of_each_category(self):
        warehouse = self.env['property.property'].create({
            'name': 'GIDC Warehouse 7', 'type_id': self.type_warehouse.id, 'total_area': 12000.0,
        })
        self.assertEqual(self.apartment.category, 'residential')
        self.assertEqual(self.office.category, 'commercial')
        self.assertEqual(warehouse.category, 'industrial')
        self.assertEqual(self.plot.category, 'land')
        self.assertEqual(self.apartment.state, 'draft')
        self.assertTrue(self.apartment.active)
        self.assertEqual(self.apartment.company_id, self.company_a)

    def test_category_follows_type(self):
        """ The category is stored once, on the type, and follows it. """
        self.apartment.type_id = self.type_office
        self.assertEqual(self.apartment.category, 'commercial')
        self.type_office.category = 'industrial'
        self.assertEqual(self.apartment.category, 'industrial')

    def test_required_fields(self):
        for missing in ('name', 'type_id'):
            vals = {'name': 'Incomplete', 'type_id': self.type_apartment.id}
            vals.pop(missing)
            with self.subTest(missing=missing), self.assertRaises(IntegrityError), \
                    mute_logger('odoo.sql_db'), self.env.cr.savepoint():
                self.env['property.property'].create(vals)
                self.env.flush_all()

    # ------------------------------------------------------------------
    # References
    # ------------------------------------------------------------------
    def test_unique_references(self):
        codes = (self.apartment | self.office | self.plot).mapped('code')
        self.assertEqual(len(set(codes)), 3)
        self.assertTrue(all(code.startswith('PROP/') for code in codes))

        duplicate = self.apartment.copy()
        self.assertTrue(duplicate.code)
        self.assertNotEqual(duplicate.code, self.apartment.code)

        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.office.code = self.apartment.code
            self.env.flush_all()

        other_company = self.env['property.property'].create({
            'name': 'Same reference elsewhere', 'type_id': self.type_apartment.id,
            'company_id': self.company_b.id, 'code': self.apartment.code,
        })
        self.assertEqual(other_company.code, self.apartment.code)

    def test_display_name_and_name_search(self):
        self.assertEqual(self.apartment.display_name, f'[{self.apartment.code}] Skyline A-205')
        found = self.env['property.property'].name_search(self.apartment.code)
        self.assertEqual([res_id for res_id, _name in found], [self.apartment.id])

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def test_negative_values_rejected(self):
        for field in ('bedrooms', 'bathrooms', 'total_area', 'land_area', 'rent_price', 'sale_price'):
            with self.subTest(field=field), self.assertRaises(IntegrityError), \
                    mute_logger('odoo.sql_db'), self.env.cr.savepoint():
                self.apartment.write({field: -1})
                self.env.flush_all()

    def test_land_has_no_rooms_or_furnishing(self):
        for vals in ({'bedrooms': 1}, {'bathrooms': 1}, {'furnishing': 'furnished'}):
            with self.subTest(vals=vals), self.assertRaises(ValidationError):
                self.plot.write(vals)

    def test_responsible_agent_must_be_real_estate_user(self):
        with self.assertRaises(ValidationError):
            self.apartment.user_id = self.internal_user
        self.apartment.user_id = self.manager
        self.assertEqual(self.apartment.user_id, self.manager)

    def test_set_available_rules(self):
        with self.assertRaises(UserError):
            self.plot.action_set_available()  # no owner
        self.plot.owner_id = self.owner
        self.plot.action_set_available()
        self.assertEqual(self.plot.state, 'available')

        self.apartment.rent_price = 0.0
        with self.assertRaises(UserError):
            self.apartment.action_set_available()
        self.apartment.rent_price = 30000.0
        self.apartment.action_set_available()
        self.assertEqual(self.apartment.state, 'available')

    def test_state_onchange_sets_country(self):
        gujarat = self.env.ref('base.state_in_gj')
        with self.env.cr.savepoint():
            form_record = self.env['property.property'].new({'state_id': gujarat.id})
            form_record._onchange_state_id()
            self.assertEqual(form_record.country_id, self.env.ref('base.in'))

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------
    def test_archive_and_restore(self):
        self.office.action_archive()
        self.assertFalse(self.office.active)
        self.assertNotIn(self.office, self.env['property.property'].search([]))
        self.assertIn(self.office, self.env['property.property'].with_context(active_test=False).search([]))
        self.office.action_unarchive()
        self.assertTrue(self.office.active)

    def test_cannot_archive_with_running_contract(self):
        contract = self.env['property.rental.contract'].create({
            'property_id': self.apartment.id, 'tenant_id': self.tenant.id,
            'date_start': date(2026, 4, 1), 'date_end': date(2027, 3, 31),
        })
        contract.action_start()
        with self.assertRaises(UserError):
            self.apartment.action_archive()
        contract.action_close()
        self.apartment.action_archive()
        self.assertFalse(self.apartment.active)

    # ------------------------------------------------------------------
    # Search and filters
    # ------------------------------------------------------------------
    def test_search_view_filters(self):
        """ Every filter of the search view evaluates and returns the expected records. """
        Property = self.env['property.property'].with_user(self.agent)
        arch = Property.get_views([(False, 'search')])['views']['search']['arch']
        filters = {
            node.get('name'): node.get('domain')
            for node in etree.fromstring(arch).iter('filter')
            if node.get('domain')
        }
        expected = {
            'for_rent': self.apartment,
            'for_sale': self.office | self.plot,
            'residential': self.apartment,
            'commercial': self.office,
            'land': self.plot,
            'furnished': self.apartment,
            'three_bedrooms': self.apartment,
            'my_properties': self.apartment,
            'no_owner': self.plot,
        }
        mine = self.apartment | self.office | self.plot
        for name, domain in filters.items():
            with self.subTest(filter=name):
                records = Property.search(safe_eval(domain, {'uid': self.agent.id}))
                if name in expected:
                    self.assertEqual(records & mine, expected[name])

        group_bys = [
            safe_eval(node.get('context'))['group_by']
            for node in etree.fromstring(arch).iter('filter')
            if node.get('context')
        ]
        for group_by in group_bys:
            with self.subTest(group_by=group_by):
                Property.formatted_read_group([], [group_by], ['__count'])

    def test_search_by_reference_city_and_postal_code(self):
        Property = self.env['property.property']
        by_reference = ['|', ('name', 'ilike', self.office.code), ('code', 'ilike', self.office.code)]
        self.assertEqual(Property.search(by_reference), self.office)
        self.assertIn(self.apartment, Property.search([('city', 'ilike', 'ahmed')]))
        self.assertIn(self.apartment, Property.search([('zip', '=', '380059')]))

    # ------------------------------------------------------------------
    # Images, documents and smart buttons
    # ------------------------------------------------------------------
    def test_images_documents_and_smart_buttons(self):
        image = self.env['property.image'].with_user(self.agent).create({
            'name': 'Living room', 'image_1920': PNG, 'property_id': self.apartment.id,
        })
        self.assertEqual(self.apartment.image_ids, image)
        self.assertEqual(image.company_id, self.company_a)

        self.assertEqual(self.apartment.document_count, 0)
        self.env['ir.attachment'].create({
            'name': 'Sale deed.pdf', 'datas': PNG,
            'res_model': 'property.property', 'res_id': self.apartment.id,
        })
        self.apartment.invalidate_recordset(['document_count'])
        self.assertEqual(self.apartment.document_count, 1)
        action = self.apartment.action_view_documents()
        self.assertEqual(self.env['ir.attachment'].search(action['domain']).name, 'Sale deed.pdf')

        self.assertEqual(self.owner.owned_property_count, 2)
        action = self.owner.action_view_owned_properties()
        self.assertEqual(self.env['property.property'].search(action['domain']), self.apartment | self.office)

        # Deleting a property removes its images.
        self.apartment.unlink()
        self.assertFalse(image.exists())

    # ------------------------------------------------------------------
    # Access rights
    # ------------------------------------------------------------------
    def test_access_rights(self):
        # Agent: create, edit, archive; no delete.
        prop = self.env['property.property'].with_user(self.agent).create({
            'name': 'Agent property', 'type_id': self.type_apartment.id,
        })
        self.assertEqual(prop.user_id, self.agent)
        prop.write({'bedrooms': 2})
        prop.action_archive()
        with self.assertRaises(AccessError):
            prop.unlink()
        # Manager: delete.
        prop.with_user(self.manager).unlink()
        # Accountant: read only, including images.
        self.assertEqual(self.apartment.with_user(self.accountant).bedrooms, 3)
        with self.assertRaises(AccessError):
            self.apartment.with_user(self.accountant).write({'bedrooms': 4})
        with self.assertRaises(AccessError):
            self.env['property.image'].with_user(self.accountant).create({
                'name': 'Nope', 'image_1920': PNG, 'property_id': self.apartment.id,
            })
        # Users without a Real Estate group see nothing.
        with self.assertRaises(AccessError):
            self.env['property.image'].with_user(self.internal_user).search([])
        with self.assertRaises(AccessError):
            self.env['property.property'].with_user(self.internal_user).search([])

    # ------------------------------------------------------------------
    # Multi-company
    # ------------------------------------------------------------------
    def test_multi_company(self):
        prop_b = self.env['property.property'].with_user(self.agent_b).create({
            'name': 'Company B Villa', 'type_id': self.type_apartment.id, 'owner_id': self.owner_b.id,
        })
        self.assertEqual(prop_b.company_id, self.company_b)

        # Agent A does not see company B properties, and agent B does not see company A's.
        self.assertNotIn(prop_b, self.env['property.property'].with_user(self.agent).search([]))
        self.assertNotIn(self.apartment, self.env['property.property'].with_user(self.agent_b).search([]))
        with self.assertRaises(AccessError):
            self.apartment.with_user(self.agent_b).read(['name'])

        # A company A property cannot use a company B owner or a company B-only agent.
        with self.assertRaises(UserError):
            self.apartment.owner_id = self.owner_b
        with self.assertRaises(UserError):
            self.apartment.user_id = self.agent_b

        # A user allowed in both companies sees both when both are active.
        self.agent.write({'company_ids': [(4, self.company_b.id)]})
        both = self.env['property.property'].with_user(self.agent).with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        ).search([])
        self.assertIn(prop_b, both)
        self.assertIn(self.apartment, both)
