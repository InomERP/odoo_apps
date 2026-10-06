# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPosAccessRights(TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.salesperson = cls.env['res.users'].create({
            'name': 'Restricted Salesperson',
            'login': 'inom_restricted_sp',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('point_of_sale.group_pos_user').id,
            ])],
        })
        cls.config.with_user(cls.salesperson).sudo().open_ui()
        cls.session = cls.config.current_session_id

    def _create_rule(self, **vals):
        return self.env['pos.access.rights'].sudo().create({'user_id': self.salesperson.id, **vals})

    def test_one_rule_per_user(self):
        self._create_rule()
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self._create_rule()
            self.env.flush_all()

    def test_rule_name_computed(self):
        rule = self._create_rule()
        self.assertIn(self.salesperson.name, rule.name)

    def test_pos_user_can_read_own_rule(self):
        rule = self._create_rule(hide_payment_button=True)
        self.assertTrue(rule.with_user(self.salesperson).read(['hide_payment_button']))

    def test_rule_loaded_in_pos_data(self):
        self._create_rule(hide_payment_button=True)
        data = self.session.with_user(self.salesperson).load_data({})
        self.assertIn('pos.access.rights', data)
        records = data['pos.access.rights']['records'] if isinstance(
            data['pos.access.rights'], dict) else data['pos.access.rights']
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]['hide_payment_button'])

    def test_search_order_ids_with_employee_restriction(self):
        """Salesperson linked to an employee must not crash the ticket screen,
        even when pos_hr (which adds pos.order.employee_id) is not installed."""
        self.env['hr.employee'].sudo().create({'name': 'SP Employee', 'user_id': self.salesperson.id})
        self._create_rule(restrict_salesperson_orders=True)
        res = self.env['pos.order'].with_user(self.salesperson).search_order_ids(
            self.config.id, [], 10, 0)
        self.assertIn('ordersInfo', res)

    def test_search_order_ids_combined_frontend_domain(self):
        """The frontend combines its search domain with the salesperson domain."""
        self._create_rule(restrict_salesperson_orders=True)
        domain = ['&', '|', ['user_id', '=', self.salesperson.id],
                  ['user_id', '=', self.salesperson.id], ['pos_reference', 'ilike', '%x%']]
        res = self.env['pos.order'].with_user(self.salesperson).search_order_ids(
            self.config.id, domain, 10, 0)
        self.assertIn('ordersInfo', res)

    def test_pos_management_permission_toggles_group(self):
        group = self.env.ref('inom_pos_access_management.group_pos_access_manager')
        user = self.salesperson.sudo()
        self.assertFalse(user.pos_management_permission)
        user.pos_management_permission = True
        self.assertIn(group, user.all_group_ids)
        user.pos_management_permission = False
        self.assertNotIn(group, user.all_group_ids)

    def test_pos_session_isolation(self):
        other_user = self.env['res.users'].sudo().create({
            'name': 'Other POS User',
            'login': 'inom_other_pos_user',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('point_of_sale.group_pos_user').id,
            ])],
        })
        Session = self.env['pos.session']
        self.assertIn(self.session, Session.with_user(self.salesperson).search([]))
        self.assertNotIn(self.session, Session.with_user(other_user).search([]))

    def test_partner_restriction_on_pos_search(self):
        other = self.env['res.partner'].sudo().create({'name': 'Inom Searchable Customer'})
        self._create_rule(restrict_salesperson_customers=True)
        data = self.session.with_user(self.salesperson).load_data({
            'models': ['res.partner'],
            'search_params': {'res.partner': {'domain': [('name', 'ilike', 'Inom Searchable')]}},
            'only_records': True,
        })
        self.assertNotIn(other.id, [p['id'] for p in data['res.partner']])

    def test_partner_restriction(self):
        own = self.env['res.partner'].sudo().create({'name': 'Own Customer', 'user_id': self.salesperson.id})
        other = self.env['res.partner'].sudo().create({'name': 'Other Customer'})
        self._create_rule(restrict_salesperson_customers=True)
        data = {'pos.config': self.config, 'pos.order': self.env['pos.order']}
        domain = self.env['res.partner'].with_user(self.salesperson)._load_pos_data_domain(data)
        partners = self.env['res.partner'].search(domain)
        self.assertNotIn(other, partners)
        self.assertIn(self.salesperson.partner_id, partners)


@tagged('post_install', '-at_install')
class TestPosAccessRightsUi(TestPointOfSaleHttpCommon):

    def test_pos_access_rights_tour(self):
        self.main_pos_config.write({
            'payment_method_ids': [(4, self.bank_payment_method.id)],
        })
        self.env['pos.access.rights'].sudo().create({
            'user_id': self.pos_user.id,
            'restrict_pos_categories': True,
            'restrict_pos_category_ids': [(6, 0, self.pos_cat_chair_test.ids)],
            'restrict_payment_method': True,
            'restrict_payment_method_ids': [(6, 0, self.bank_payment_method.ids)],
            'disable_qty_button': True,
            'hide_close_pos_button': True,
            'hide_backend_pos_button': True,
            'hide_cash_in_out_button': True,
            'hide_payment_invoice_button': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('InomPosAccessRightsTour', login='pos_user')

    def test_pos_access_rights_actions_tour(self):
        self.env['pos.access.rights'].sudo().create({
            'user_id': self.pos_user.id,
            'hide_customer_note_button': True,
            'hide_pricelist_button': True,
            'hide_info_button': True,
            'hide_delete_order_button': True,
            'hide_payment_button': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('InomPosAccessRightsActionsTour', login='pos_user')
