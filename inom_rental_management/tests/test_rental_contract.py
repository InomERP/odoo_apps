import importlib.util
from datetime import date, timedelta
from os.path import dirname, join

from dateutil.relativedelta import relativedelta
from psycopg2 import errors as pg_errors

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestRentalContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(cls.env, 'p6_agent', groups='inom_rental_management.group_rental_agent')
        cls.agent_2 = new_test_user(cls.env, 'p6_agent_2', groups='inom_rental_management.group_rental_agent')
        cls.manager = new_test_user(cls.env, 'p6_manager', groups='inom_rental_management.group_rental_manager')
        cls.accountant = new_test_user(cls.env, 'p6_accountant', groups='inom_rental_management.group_rental_accountant')

        cls.property_type = cls.env['property.type'].create({'name': 'Apartment P6', 'category': 'residential'})
        cls.owner = cls.env['res.partner'].create({'name': 'P6 Owner', 'is_property_owner': True})
        cls.tenant = cls.env['res.partner'].create({'name': 'P6 Tenant', 'is_tenant': True})
        cls.tenant_2 = cls.env['res.partner'].create({'name': 'P6 Tenant 2', 'is_tenant': True})
        cls.flat = cls.env['property.property'].create({
            'name': 'Skyline C-101', 'type_id': cls.property_type.id, 'owner_id': cls.owner.id,
            'rent_price': 20000.0, 'user_id': cls.agent.id,
        })
        cls.flat.action_set_available()
        cls.today = fields.Date.context_today(cls.env.user)

    def _lease(self, user=None, **kwargs):
        vals = {
            'property_id': self.flat.id, 'tenant_id': self.tenant.id, 'user_id': self.agent.id,
            'date_start': self.today, 'date_end': self.today + relativedelta(years=1, days=-1),
            'deposit_amount': 60000.0,
        }
        vals.update(kwargs)
        Contract = self.env['property.rental.contract']
        return (Contract.with_user(user) if user else Contract).create(vals)

    # ------------------------------------------------------------------
    # Creation and dates
    # ------------------------------------------------------------------
    def test_create_contract(self):
        lease = self._lease(user=self.agent)
        self.assertTrue(lease.name.startswith('RC/'))
        self.assertEqual(lease.state, 'draft')
        self.assertEqual(lease.property_id, self.flat)
        self.assertEqual(lease.tenant_id, self.tenant)
        self.assertEqual(lease.owner_id, self.owner)
        self.assertEqual(lease.rent_amount, 20000.0, "Monthly rent defaults to the property's rental price")
        self.assertEqual(lease.rent_period, 'monthly')
        self.assertEqual(lease.deposit_amount, 60000.0)
        self.assertEqual(lease.company_id, self.env.company)
        self.assertEqual(self.flat.state, 'available', "A draft lease does not change the property")

    def test_invalid_dates(self):
        with self.assertRaises(ValidationError):
            self._lease(date_end=self.today - timedelta(days=1))
        with self.assertRaises(ValidationError):
            self._lease(date_end=self.today)

    def test_terms_locked_after_approval(self):
        lease = self._lease()
        lease.write({'rent_amount': 21000.0})  # free while draft
        lease.with_user(self.manager).action_approve()
        for vals in ({'rent_amount': 1.0}, {'date_end': self.today + relativedelta(years=3)}, {'tenant_id': self.tenant_2.id}):
            with self.subTest(vals=vals), self.assertRaises(UserError):
                lease.write(vals)
        lease.write({'note': '<p>Notes stay editable</p>'})

    # ------------------------------------------------------------------
    # Transitions and permissions
    # ------------------------------------------------------------------
    def test_lifecycle(self):
        lease = self._lease(user=self.agent)
        lease.with_user(self.manager).action_approve()
        self.assertEqual(lease.state, 'approved')
        self.assertEqual(lease.approved_by_id, self.manager)
        self.assertEqual(self.flat.state, 'available', "Approval reserves the dates, not the property status")
        lease.with_user(self.agent).action_start()
        self.assertEqual(lease.state, 'running')
        self.assertEqual(self.flat.state, 'rented')
        lease.with_user(self.manager).action_close()
        self.assertEqual(lease.state, 'closed')
        self.assertEqual(lease.date_closed, self.today)
        self.assertEqual(self.flat.state, 'available')

    def test_approval_setting(self):
        lease = self._lease()
        lease.action_start()  # approval not required by default
        self.assertEqual(lease.state, 'running')

        self.env.company.rental_require_lease_approval = True
        lease_2 = self._lease(user=self.agent, date_start=lease.date_end + timedelta(days=1),
                              date_end=lease.date_end + relativedelta(years=1))
        with self.assertRaises(UserError):
            lease_2.with_user(self.agent).action_start()
        with self.assertRaises(AccessError):
            lease_2.with_user(self.agent).action_approve()
        lease_2.with_user(self.manager).action_approve()
        lease_2.with_user(self.agent).action_start()
        self.assertEqual(lease_2.state, 'running')

    def test_invalid_transitions(self):
        lease = self._lease()
        for method in ('action_close', 'action_open_renew_wizard', 'action_open_terminate_wizard'):
            with self.subTest(state='draft', method=method), self.assertRaises(UserError):
                getattr(lease, method)()
        lease.action_start()
        for method in ('action_approve', 'action_start', 'action_cancel', 'action_reset_to_draft'):
            with self.subTest(state='running', method=method), self.assertRaises(UserError):
                getattr(lease, method)()
        lease.action_close()
        for method in ('action_start', 'action_close', 'action_cancel', 'action_open_renew_wizard',
                       'action_open_terminate_wizard', 'action_reset_to_draft'):
            with self.subTest(state='closed', method=method), self.assertRaises(UserError):
                getattr(lease, method)()

    def test_cancel_and_reset(self):
        lease = self._lease(user=self.agent)
        lease.with_user(self.manager).action_approve()
        with self.assertRaises(AccessError):
            lease.with_user(self.agent).action_reset_to_draft()
        lease.with_user(self.agent).action_cancel()
        self.assertEqual(lease.state, 'cancelled')
        lease.with_user(self.agent).action_reset_to_draft()
        self.assertEqual(lease.state, 'draft')
        self.assertFalse(lease.approved_by_id)

    def test_permissions(self):
        lease = self._lease(user=self.agent)
        # Another agent cannot see or act on it.
        self.assertNotIn(lease, self.env['property.rental.contract'].with_user(self.agent_2).search([]))
        with self.assertRaises(AccessError):
            lease.with_user(self.agent_2).action_start()
        # The accountant reads all contracts but changes none.
        self.assertIn(lease, self.env['property.rental.contract'].with_user(self.accountant).search([]))
        with self.assertRaises(AccessError):
            lease.with_user(self.accountant).action_start()
        with self.assertRaises(AccessError):
            self._lease(user=self.accountant)
        lease.with_user(self.agent).action_start()
        # Agents may close only once the end date has passed; termination is for managers.
        with self.assertRaises(AccessError):
            lease.with_user(self.agent).action_close()
        with self.assertRaises(AccessError):
            lease.with_user(self.agent).action_open_terminate_wizard()
        with self.assertRaises(AccessError):
            self.env['property.rental.contract.terminate'].with_user(self.agent).create({
                'contract_id': lease.id, 'termination_reason': 'other',
            })
        # Agents may renew their own leases.
        renew = self.env['property.rental.contract.renew'].with_user(self.agent).create({'contract_id': lease.id})
        renew.action_renew()
        self.assertTrue(lease.renewal_id)

    def test_history_is_never_deleted(self):
        old = self._lease(date_start=self.today - relativedelta(years=2), date_end=self.today - relativedelta(years=1, days=1))
        old.action_start()
        old.action_close()
        new = self._lease()
        new.action_start()
        for contract in (old, new):
            with self.subTest(contract=contract.name), self.assertRaises(UserError):
                contract.unlink()
        self.assertEqual(self.flat.rental_contract_ids, old | new)
        self.assertEqual(self.tenant.tenant_contract_ids, old | new)
        draft = self._lease(date_start=self.today + relativedelta(years=3), date_end=self.today + relativedelta(years=4))
        draft.with_user(self.manager).unlink()

    # ------------------------------------------------------------------
    # Overlap
    # ------------------------------------------------------------------
    def test_overlapping_contracts(self):
        first = self._lease()
        first.action_start()
        overlapping = self._lease(tenant_id=self.tenant_2.id, date_start=self.today + relativedelta(months=6),
                                  date_end=self.today + relativedelta(months=18))
        with self.assertRaises(UserError):
            overlapping.with_user(self.manager).action_approve()
        with self.assertRaises(UserError):
            overlapping.action_start()
        self.assertEqual(overlapping.state, 'draft', "Draft offers may overlap; they just cannot become active")

        # An approved future lease also blocks the dates.
        future = self._lease(tenant_id=self.tenant_2.id, date_start=first.date_end + timedelta(days=1),
                             date_end=first.date_end + relativedelta(years=1))
        future.with_user(self.manager).action_approve()
        clash = self._lease(tenant_id=self.tenant_2.id, date_start=first.date_end + relativedelta(months=2),
                            date_end=first.date_end + relativedelta(months=5))
        with self.assertRaises(UserError):
            clash.action_start()

        # The approved future lease still blocks months 13 to 18 of the overlapping offer.
        first.action_close()
        with self.assertRaises(UserError):
            overlapping.action_start()
        # Ended or cancelled contracts no longer block.
        future.action_cancel()
        overlapping.action_start()
        self.assertEqual(overlapping.state, 'running')

    def test_adjacent_contracts_do_not_overlap(self):
        first = self._lease()
        first.action_start()
        nxt = self._lease(tenant_id=self.tenant_2.id, date_start=first.date_end + timedelta(days=1),
                          date_end=first.date_end + relativedelta(years=1))
        nxt.with_user(self.manager).action_approve()
        self.assertEqual(nxt.state, 'approved')

    def test_overlap_allowed_on_shared_property(self):
        self.flat.allow_multiple_leases = True
        first = self._lease()
        first.action_start()
        second = self._lease(tenant_id=self.tenant_2.id)
        second.action_start()
        self.assertEqual((first | second).mapped('state'), ['running', 'running'])
        first.action_close()
        self.assertEqual(self.flat.state, 'rented', "The property stays rented while another lease runs")
        second.action_close()
        self.assertEqual(self.flat.state, 'available')

    @mute_logger('odoo.sql_db')
    def test_concurrent_starts_are_serialised(self):
        """ Two users start conflicting leases at the same time, in separate transactions:
        the second fails instead of silently creating a double letting. """
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            ptype = env['property.type'].create({'name': 'P6 concurrency type', 'category': 'residential'})
            owner = env['res.partner'].create({'name': 'P6 concurrency owner', 'is_property_owner': True})
            tenants = env['res.partner'].create([
                {'name': 'P6 concurrency tenant A', 'is_tenant': True},
                {'name': 'P6 concurrency tenant B', 'is_tenant': True},
            ])
            prop = env['property.property'].create({
                'name': 'P6 concurrency flat', 'type_id': ptype.id, 'owner_id': owner.id, 'rent_price': 100.0,
            })
            leases = env['property.rental.contract'].create([{
                'property_id': prop.id, 'tenant_id': tenant.id,
                'date_start': date(2030, 1, 1), 'date_end': date(2030, 12, 31),
            } for tenant in tenants])
            ids = {'type': ptype.id, 'partners': (owner | tenants).ids, 'property': prop.id, 'leases': leases.ids}
        try:
            with self.registry.cursor() as cr_a, self.registry.cursor() as cr_b:
                env_a = api.Environment(cr_a, SUPERUSER_ID, {})
                env_b = api.Environment(cr_b, SUPERUSER_ID, {})
                lease_a = env_a['property.rental.contract'].browse(ids['leases'][0])
                lease_b = env_b['property.rental.contract'].browse(ids['leases'][1])
                lease_b.read(['state'])  # transaction B is already running when A commits
                lease_a.action_start()
                cr_a.commit()
                with self.assertRaises(pg_errors.SerializationFailure):
                    lease_b.action_start()
                    env_b.flush_all()
                cr_b.rollback()
                env_b.invalidate_all()
                # Odoo retries a request that hit a serialization failure: the retry sees A's lease.
                with self.assertRaises(UserError):
                    lease_b.action_start()
                cr_b.rollback()
                env_b.invalidate_all()
                self.assertEqual(lease_b.state, 'draft')
                self.assertEqual(env_b['property.rental.contract'].browse(ids['leases'][0]).state, 'running')
        finally:
            with self.registry.cursor() as cr:
                cr.execute('DELETE FROM property_rental_contract WHERE id IN %s', [tuple(ids['leases'])])
                cr.execute('DELETE FROM property_property WHERE id = %s', [ids['property']])
                cr.execute('DELETE FROM res_partner WHERE id IN %s', [tuple(ids['partners'])])
                cr.execute('DELETE FROM property_type WHERE id = %s', [ids['type']])

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------
    def test_expiry_tracking(self):
        ended = self._lease(date_start=self.today - relativedelta(years=1), date_end=self.today - timedelta(days=1))
        ended.action_start()
        ending = self._lease(property_id=self.flat.copy({'name': 'Skyline C-102'}).id,
                             date_start=self.today - relativedelta(months=11), date_end=self.today + timedelta(days=20))
        ending.action_start()
        later = self._lease(property_id=self.flat.copy({'name': 'Skyline C-103'}).id,
                            date_end=self.today + relativedelta(years=2))
        later.action_start()
        self.assertEqual(ending.days_to_expiry, 20)

        Contract = self.env['property.rental.contract']
        Contract._cron_update_lease_status()
        self.assertEqual(ended.state, 'expired')
        self.assertEqual(ended.property_id.state, 'rented', "An expired lease still holds the property")
        self.assertEqual(ending.state, 'running')
        self.assertEqual(len(ending.activity_ids), 1, "A reminder is scheduled before the end date")
        self.assertFalse(later.activity_ids)
        Contract._cron_update_lease_status()
        self.assertEqual(len(ending.activity_ids), 1, "The reminder is not duplicated")

        # The Expiring in 30 Days filter finds the lease about to end.
        domain = [('state', '=', 'running'), ('date_end', '>=', self.today),
                  ('date_end', '<=', self.today + relativedelta(days=30))]
        self.assertEqual(Contract.search(domain) & (ended | ending | later), ending)

        # An expired lease can still be closed by its agent, since its end date has passed.
        ended.with_user(self.agent).action_close()
        self.assertEqual(ended.state, 'closed')

    # ------------------------------------------------------------------
    # Renewal
    # ------------------------------------------------------------------
    def test_renewal(self):
        lease = self._lease(date_start=self.today - relativedelta(years=1), date_end=self.today + timedelta(days=10),
                            rent_amount=20000.0)
        lease.action_start()
        wizard = self.env['property.rental.contract.renew'].with_context(
            default_contract_id=lease.id,
        ).create({'increase_percent': 5.0})
        self.assertEqual(wizard.date_start, lease.date_end + timedelta(days=1))
        self.assertEqual(wizard.rent_amount, 21000.0)
        action = wizard.action_renew()
        renewal = self.env['property.rental.contract'].browse(action['res_id'])

        self.assertEqual(renewal.state, 'draft')
        self.assertEqual(renewal.renewed_from_id, lease)
        self.assertEqual(lease.renewal_id, renewal)
        self.assertEqual((renewal.property_id, renewal.tenant_id), (lease.property_id, lease.tenant_id))
        self.assertEqual(renewal.deposit_amount, lease.deposit_amount)
        self.assertEqual(renewal.rent_amount, 21000.0)
        self.assertEqual(lease.state, 'running', "Renewing does not end the current lease")

        with self.assertRaises(UserError):
            lease.action_open_renew_wizard()  # only one renewal
        renewal.action_start()  # adjacent dates, so no overlap
        self.assertEqual(lease.state, 'running', "The current lease runs until its own end date")
        with self.assertRaises(UserError):
            self.env['property.rental.contract'].create({
                'renewed_from_id': lease.id, 'property_id': self.flat.id, 'tenant_id': self.tenant.id,
                'date_start': lease.date_end + timedelta(days=1), 'date_end': lease.date_end + relativedelta(years=1),
            })

    def test_renewal_validation(self):
        lease = self._lease()
        lease.action_start()
        with self.assertRaises(ValidationError):
            lease._renew(lease.date_end, lease.date_end + relativedelta(years=1), 1000.0)  # starts before the end
        with self.assertRaises(ValidationError):
            self.env['property.rental.contract'].create({
                'renewed_from_id': lease.id, 'property_id': self.flat.id, 'tenant_id': self.tenant_2.id,
                'date_start': lease.date_end + timedelta(days=1), 'date_end': lease.date_end + relativedelta(years=1),
            })

    def test_expired_lease_closed_when_renewal_takes_over(self):
        lease = self._lease(date_start=self.today - relativedelta(years=1), date_end=self.today - timedelta(days=2))
        lease.action_start()
        self.env['property.rental.contract']._cron_update_lease_status()
        self.assertEqual(lease.state, 'expired')
        renewal = lease._renew(lease.date_end + timedelta(days=1), lease.date_end + relativedelta(years=1), 22000.0)
        renewal.action_start()
        self.assertEqual(lease.state, 'closed')
        self.assertEqual(renewal.state, 'running')
        self.assertEqual(self.flat.state, 'rented')

    def test_cron_closes_ended_lease_with_running_renewal(self):
        lease = self._lease(date_start=self.today - relativedelta(years=1), date_end=self.today + timedelta(days=5))
        lease.action_start()
        renewal = lease._renew(lease.date_end + timedelta(days=1), lease.date_end + relativedelta(years=1), 20000.0)
        renewal.action_start()
        lease.flush_recordset()
        self.env.cr.execute('UPDATE property_rental_contract SET date_end = %s WHERE id = %s',
                            [self.today - timedelta(days=1), lease.id])
        lease.invalidate_recordset()
        self.env['property.rental.contract']._cron_update_lease_status()
        self.assertEqual(lease.state, 'closed')

    # ------------------------------------------------------------------
    # Termination
    # ------------------------------------------------------------------
    def test_early_termination(self):
        lease = self._lease(date_start=self.today - relativedelta(months=3))
        lease.action_start()
        renewal_draft = lease._renew(lease.date_end + timedelta(days=1), lease.date_end + relativedelta(years=1), 1.0)
        Wizard = self.env['property.rental.contract.terminate'].with_user(self.manager)
        with self.assertRaises(UserError):
            Wizard.create({'contract_id': lease.id, 'date_terminated': lease.date_start - timedelta(days=1),
                           'termination_reason': 'tenant_request'}).action_terminate()
        with self.assertRaises(UserError):
            Wizard.create({'contract_id': lease.id, 'date_terminated': lease.date_end + timedelta(days=1),
                           'termination_reason': 'tenant_request'}).action_terminate()
        Wizard.create({
            'contract_id': lease.id, 'date_terminated': self.today, 'termination_reason': 'non_payment',
            'termination_note': 'Two months unpaid',
        }).action_terminate()
        self.assertEqual(lease.state, 'terminated')
        self.assertEqual(lease.date_terminated, self.today)
        self.assertEqual(lease.termination_reason, 'non_payment')
        self.assertEqual(lease.termination_note, 'Two months unpaid')
        self.assertEqual(lease.date_end, self.today + relativedelta(years=1, days=-1), "The agreed end date is kept")
        self.assertEqual(self.flat.state, 'available')
        self.assertEqual(renewal_draft.state, 'cancelled', "A pending renewal is cancelled with the lease")

        # The property can be let again; the terminated lease stays in the history.
        new = self._lease(tenant_id=self.tenant_2.id, date_start=self.today + timedelta(days=1),
                          date_end=self.today + relativedelta(years=1))
        new.action_start()
        self.assertIn(lease, self.flat.rental_contract_ids)

    # ------------------------------------------------------------------
    # Upgrade
    # ------------------------------------------------------------------
    def test_migration_marks_let_properties_rented(self):
        lease = self._lease()
        lease.action_start()
        self.env.flush_all()
        self.env.cr.execute("UPDATE property_property SET state = 'available' WHERE id = %s", [self.flat.id])
        path = join(dirname(dirname(__file__)), 'migrations', '19.0.1.4.0', 'post-migrate.py')
        spec = importlib.util.spec_from_file_location('rental_management_post_migrate_1_4', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, '19.0.1.3.0')
        self.env.invalidate_all()
        self.assertEqual(self.flat.state, 'rented')
