from datetime import date

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestRentalManagement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(cls.env, 'rm_agent', groups='inom_rental_management.group_rental_agent')
        cls.agent_2 = new_test_user(cls.env, 'rm_agent_2', groups='inom_rental_management.group_rental_agent')
        cls.manager = new_test_user(cls.env, 'rm_manager', groups='inom_rental_management.group_rental_manager')
        cls.admin = new_test_user(cls.env, 'rm_admin', groups='inom_rental_management.group_rental_admin')
        cls.accountant = new_test_user(cls.env, 'rm_accountant', groups='inom_rental_management.group_rental_accountant')
        cls.internal_user = new_test_user(cls.env, 'rm_internal', groups='base.group_user')

        cls.property_type = cls.env['property.type'].create({'name': 'Apartment RM Test', 'category': 'residential'})
        cls.owner = cls.env['res.partner'].create({'name': 'Rajesh Mehta', 'is_property_owner': True})
        cls.tenant = cls.env['res.partner'].create({'name': 'Neha Kulkarni', 'is_tenant': True})
        cls.buyer = cls.env['res.partner'].create({'name': 'Karan Desai', 'is_property_buyer': True})
        cls.rent_property = cls.env['property.property'].create({
            'name': 'Skyline A-101',
            'type_id': cls.property_type.id,
            'property_for': 'rent',
            'owner_id': cls.owner.id,
            'rent_price': 32000.0,
        })
        cls.sale_property = cls.env['property.property'].create({
            'name': 'Skyline B-301',
            'type_id': cls.property_type.id,
            'property_for': 'sale',
            'owner_id': cls.owner.id,
            'sale_price': 9000000.0,
        })

    def _rental_vals(self, **kwargs):
        return {
            'property_id': self.rent_property.id,
            'tenant_id': self.tenant.id,
            'date_start': date(2026, 4, 1),
            'date_end': date(2027, 3, 31),
            **kwargs,
        }

    def _visible_menus(self, user):
        """ Menus the web client shows: the menu and all its ancestors are visible. """
        menu_ids = self.env['ir.ui.menu'].with_user(user)._visible_menu_ids()
        visible = set()
        for xmlid in (
            'menu_rental_management_root', 'menu_rental_properties', 'menu_rental_owners',
            'menu_rental_tenants', 'menu_rental_contracts', 'menu_rental_sales',
            'menu_rental_sale_contracts', 'menu_rental_buyers', 'menu_rental_reports',
            'menu_rental_configuration', 'menu_rental_property_types', 'menu_rental_amenities',
        ):
            menu = self.env.ref(f'inom_rental_management.{xmlid}')
            ancestor_ids = [int(menu_id) for menu_id in menu.parent_path.split('/') if menu_id]
            if all(menu_id in menu_ids for menu_id in ancestor_ids):
                visible.add(xmlid)
        return visible

    def test_group_hierarchy(self):
        self.assertTrue(self.admin.has_group('inom_rental_management.group_rental_manager'))
        self.assertTrue(self.admin.has_group('inom_rental_management.group_rental_agent'))
        self.assertTrue(self.manager.has_group('inom_rental_management.group_rental_agent'))
        self.assertFalse(self.manager.has_group('inom_rental_management.group_rental_admin'))
        self.assertFalse(self.accountant.has_group('inom_rental_management.group_rental_agent'))
        self.assertTrue(self.accountant.has_group('account.group_account_invoice'))
        self.assertTrue(self.env.ref('base.user_admin').has_group('inom_rental_management.group_rental_admin'))

    def test_menus_per_group(self):
        operations = {
            'menu_rental_management_root', 'menu_rental_properties', 'menu_rental_owners',
            'menu_rental_tenants', 'menu_rental_contracts', 'menu_rental_sales',
            'menu_rental_sale_contracts', 'menu_rental_buyers',
        }
        reports = {'menu_rental_reports'}
        configuration = {'menu_rental_configuration', 'menu_rental_property_types', 'menu_rental_amenities'}

        self.assertEqual(self._visible_menus(self.agent), operations)
        self.assertEqual(self._visible_menus(self.manager), operations | reports)
        self.assertEqual(self._visible_menus(self.admin), operations | reports | configuration)
        self.assertEqual(self._visible_menus(self.accountant), operations | reports)
        self.assertEqual(self._visible_menus(self.internal_user), set())

    def test_agent_access(self):
        Property = self.env['property.property'].with_user(self.agent)
        new_property = Property.create({'name': 'Skyline A-102', 'type_id': self.property_type.id})
        new_property.write({'rent_price': 25000.0})
        with self.assertRaises(AccessError):
            new_property.unlink()
        with self.assertRaises(AccessError):
            self.env['property.type'].with_user(self.agent).create({'name': 'Villa'})

        own_contract = self.env['property.rental.contract'].with_user(self.agent).create(self._rental_vals())
        other_contract = self.env['property.rental.contract'].with_user(self.agent_2).create(self._rental_vals())
        visible = self.env['property.rental.contract'].with_user(self.agent).search([])
        self.assertIn(own_contract, visible)
        self.assertNotIn(other_contract, visible)
        with self.assertRaises(AccessError):
            other_contract.with_user(self.agent).read(['name'])
        with self.assertRaises(AccessError):
            own_contract.with_user(self.agent).unlink()

        own_sale = self.env['property.sale.contract'].with_user(self.agent).create({
            'property_id': self.sale_property.id, 'buyer_id': self.buyer.id,
        })
        other_sale = self.env['property.sale.contract'].with_user(self.agent_2).create({
            'property_id': self.sale_property.id, 'buyer_id': self.buyer.id,
        })
        visible_sales = self.env['property.sale.contract'].with_user(self.agent).search([])
        self.assertIn(own_sale, visible_sales)
        self.assertNotIn(other_sale, visible_sales)

    def test_manager_access(self):
        contract_1 = self.env['property.rental.contract'].with_user(self.agent).create(self._rental_vals())
        contract_2 = self.env['property.rental.contract'].with_user(self.agent_2).create(self._rental_vals())
        visible = self.env['property.rental.contract'].with_user(self.manager).search([])
        self.assertIn(contract_1, visible)
        self.assertIn(contract_2, visible)
        contract_2.with_user(self.manager).unlink()

        new_property = self.env['property.property'].with_user(self.manager).create({
            'name': 'Temporary', 'type_id': self.property_type.id,
        })
        new_property.unlink()
        with self.assertRaises(AccessError):
            self.env['property.type'].with_user(self.manager).create({'name': 'Villa'})

    def test_admin_access(self):
        new_type = self.env['property.type'].with_user(self.admin).create({'name': 'Villa RM Test'})
        amenity = self.env['property.amenity'].with_user(self.admin).create({'name': 'Rooftop Deck RM Test'})
        new_type.write({'sequence': 5})
        amenity.unlink()
        new_type.unlink()

    def test_accountant_access(self):
        contract = self.env['property.rental.contract'].with_user(self.agent).create(self._rental_vals())
        self.assertEqual(self.rent_property.with_user(self.accountant).name, 'Skyline A-101')
        self.assertIn(contract, self.env['property.rental.contract'].with_user(self.accountant).search([]))
        with self.assertRaises(AccessError):
            self.rent_property.with_user(self.accountant).write({'rent_price': 1.0})
        with self.assertRaises(AccessError):
            contract.with_user(self.accountant).write({'rent_amount': 1.0})
        with self.assertRaises(AccessError):
            self.env['property.property'].with_user(self.accountant).create({
                'name': 'Not allowed', 'type_id': self.property_type.id,
            })

    def test_internal_user_without_group(self):
        with self.assertRaises(AccessError):
            self.rent_property.with_user(self.internal_user).read(['name'])
        # The partner form must still open for users outside the Real Estate groups.
        views = self.env['res.partner'].with_user(self.internal_user).get_views([(False, 'form')])
        self.assertNotIn('owned_property_ids', views['views']['form']['arch'])

    def test_sequences_and_defaults(self):
        self.assertTrue(self.rent_property.code.startswith('PROP/'))
        self.assertNotEqual(self.rent_property.code, self.sale_property.code)
        contract = self.env['property.rental.contract'].create(self._rental_vals())
        self.assertTrue(contract.name.startswith('RC/'))
        self.assertEqual(contract.rent_amount, 32000.0)
        self.assertEqual(contract.owner_id, self.owner)
        sale = self.env['property.sale.contract'].create({
            'property_id': self.sale_property.id, 'buyer_id': self.buyer.id,
        })
        self.assertTrue(sale.name.startswith('SC/'))
        self.assertEqual(sale.sale_price, 9000000.0)
        self.assertEqual(self.rent_property.rental_contract_count, 1)

    def test_contract_dates_constraint(self):
        with self.assertRaises(ValidationError):
            self.env['property.rental.contract'].create(self._rental_vals(date_end=date(2026, 3, 1)))

    def test_workflows(self):
        self.rent_property.action_set_available()
        self.assertEqual(self.rent_property.state, 'available')

        contract = self.env['property.rental.contract'].create(self._rental_vals())
        contract.action_start()
        self.assertEqual(contract.state, 'running')
        contract.action_close()
        self.assertEqual(contract.state, 'closed')

        sale = self.env['property.sale.contract'].create({
            'property_id': self.sale_property.id, 'buyer_id': self.buyer.id,
        })
        sale.action_book()
        self.assertEqual(sale.state, 'booked')
        sale.action_cancel()
        self.assertEqual(sale.state, 'cancelled')
        sale.action_reset_to_draft()
        self.assertEqual(sale.state, 'draft')
