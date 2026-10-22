from datetime import date
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.inom_rental_management_maintenance.models import rental_demo as maintenance_demo


@tagged('post_install', '-at_install')
class TestPropertyMaintenance(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        cls.env.user.group_ids += cls.env.ref('inom_rental_management.group_rental_admin') \
            + cls.env.ref('maintenance.group_equipment_manager')
        cls.agent = new_test_user(cls.env, 'p10_agent', groups='inom_rental_management.group_rental_agent')
        cls.agent_2 = new_test_user(cls.env, 'p10_agent_2', groups='inom_rental_management.group_rental_agent')
        cls.manager = new_test_user(cls.env, 'p10_manager', groups='inom_rental_management.group_rental_manager')
        cls.accountant = new_test_user(cls.env, 'p10_accountant', groups='inom_rental_management.group_rental_accountant')
        cls.technician = new_test_user(cls.env, 'p10_technician', groups='base.group_user')
        cls.employee_user = new_test_user(cls.env, 'p10_employee', groups='base.group_user')
        for user in (cls.agent, cls.agent_2, cls.manager, cls.accountant, cls.technician, cls.employee_user):
            user.write({'company_id': company.id, 'company_ids': [Command.set(company.ids)]})

        cls.team = cls.env['maintenance.team'].create({'name': 'Electrical team P10'})
        ptype = cls.env['property.type'].create({'name': 'Flat P10', 'category': 'residential'})
        cls.owner = cls.env['res.partner'].create({'name': 'P10 Owner', 'is_property_owner': True})
        cls.tenant = cls.env['res.partner'].create({'name': 'P10 Tenant', 'is_tenant': True})
        cls.flat = cls.env['property.property'].create({
            'name': 'Skyline F-601', 'type_id': ptype.id, 'owner_id': cls.owner.id, 'rent_price': 15000.0,
            'user_id': cls.agent.id, 'maintenance_team_id': cls.team.id, 'technician_user_id': cls.technician.id,
        })
        cls.other_flat = cls.flat.copy({'name': 'Skyline F-602', 'user_id': cls.agent_2.id})
        cls.lease = cls.env['property.rental.contract'].create({
            'property_id': cls.flat.id, 'tenant_id': cls.tenant.id, 'user_id': cls.agent.id,
            'date_start': date(2026, 1, 1), 'date_end': date(2026, 12, 31),
        })
        cls.lease.action_start()
        stages = cls.env['maintenance.stage'].search([], order='sequence, id')
        cls.stage_new = stages[0]
        cls.stage_progress = cls.env.ref('maintenance.stage_1')
        cls.stage_done = cls.env.ref('maintenance.stage_3')

    def _request(self, user=None, **vals):
        values = {'name': 'Leaking tap', 'property_id': self.flat.id, 'maintenance_team_id': self.team.id}
        values.update(vals)
        Request = self.env['maintenance.request']
        return (Request.with_user(user) if user else Request).create(values)

    # ------------------------------------------------------------------
    # Creating requests
    # ------------------------------------------------------------------
    def test_create_from_property(self):
        action = self.flat.with_user(self.agent).action_new_maintenance_request()
        with Form(self.env['maintenance.request'].with_user(self.agent).with_context(action['context'])) as form:
            form.name = 'Lift stops between floors'
            form.priority = '3'
            form.schedule_date = fields.Datetime.now()
        request = form.save()
        self.assertEqual(request.property_id, self.flat)
        self.assertEqual(request.maintenance_team_id, self.team, "The property's team is used")
        self.assertEqual(request.user_id, self.technician, "The property's default responsible is used")
        self.assertEqual(request.rental_contract_id, self.lease, "The running lease is linked")
        self.assertEqual(request.tenant_id, self.tenant)
        self.assertEqual(request.priority, '3')
        self.assertEqual(request.stage_id, self.stage_new)
        self.assertEqual(request.owner_user_id, self.agent)

    def test_create_from_lease(self):
        action = self.lease.action_new_maintenance_request()
        request = self.env['maintenance.request'].with_context(action['context']).create({'name': 'Broken window'})
        self.assertEqual((request.property_id, request.rental_contract_id), (self.flat, self.lease))
        self.assertEqual(self.lease.maintenance_request_count, 1)
        self.assertEqual(self.env['maintenance.request'].search(self.lease.action_view_maintenance_requests()['domain']), request)

    def test_attachments(self):
        request = self._request()
        self.env['ir.attachment'].create({
            'name': 'leak.jpg', 'raw': b'jpeg', 'res_model': 'maintenance.request', 'res_id': request.id,
        })
        self.assertEqual(request.message_attachment_count, 1)

    # ------------------------------------------------------------------
    # Property relationships
    # ------------------------------------------------------------------
    def test_property_relationships(self):
        open_request = self._request()
        done_request = self._request(name='Repaint wall', user_id=self.technician.id)
        done_request.stage_id = self.stage_done
        self.assertEqual(self.flat.maintenance_ids, open_request | done_request)
        self.assertEqual(self.flat.maintenance_count, 2)
        self.assertEqual(self.flat.maintenance_open_count, 1)
        found = self.env['maintenance.request'].search(self.flat.action_view_maintenance_requests()['domain'])
        self.assertEqual(found, open_request | done_request)

    def test_lease_must_match_property(self):
        with self.assertRaises(ValidationError):
            self._request(property_id=self.other_flat.id, rental_contract_id=self.lease.id)

    # ------------------------------------------------------------------
    # Assignment and status
    # ------------------------------------------------------------------
    def test_assignment_and_status(self):
        request = self._request(user_id=False)
        with self.assertRaises(UserError):
            request.stage_id = self.stage_done  # nobody assigned
        request.user_id = self.technician
        request.stage_id = self.stage_progress
        self.assertFalse(request.close_date)
        request.stage_id = self.stage_done
        self.assertTrue(request.done)
        self.assertEqual(request.close_date, fields.Date.today())
        with self.assertRaises(UserError):
            request.user_id = False  # a closed request keeps its responsible person
        request.stage_id = self.stage_progress
        self.assertFalse(request.close_date, "Reopening clears the close date")

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    def test_permissions(self):
        mine = self._request(user=self.agent)
        theirs = self._request(user=self.agent_2, property_id=self.other_flat.id, name='Door lock')
        Request = self.env['maintenance.request']
        # Agents see the requests of their own properties, not a colleague's.
        self.assertIn(mine, Request.with_user(self.agent).search([]))
        self.assertNotIn(theirs, Request.with_user(self.agent).search([]))
        # Managers see all property requests.
        self.assertTrue((mine | theirs) <= Request.with_user(self.manager).search([]))
        # Accountants read them but cannot change them.
        self.assertIn(mine, Request.with_user(self.accountant).search([]))
        with self.assertRaises(AccessError):
            mine.with_user(self.accountant).write({'name': 'Changed'})
        # Other employees cannot attach requests to properties, nor see property requests of others.
        with self.assertRaises(AccessError):
            self._request(user=self.employee_user)
        self.assertNotIn(mine, Request.with_user(self.employee_user).search([]))
        # Their own non-property requests work as usual.
        own = Request.with_user(self.employee_user).create({'name': 'Printer jam', 'maintenance_team_id': self.team.id})
        self.assertIn(own, Request.with_user(self.employee_user).search([]))
        # The responsible technician sees the request assigned to them (standard rule).
        mine.user_id = self.technician
        self.assertIn(mine, Request.with_user(self.technician).search([]))

    def test_only_managers_set_costs(self):
        request = self._request(user=self.agent)
        with self.assertRaises(AccessError):
            request.with_user(self.agent).write({'maintenance_cost': 500.0})
        request.with_user(self.manager).write({'maintenance_cost': 500.0, 'cost_charged_to': 'tenant',
                                               'rental_contract_id': self.lease.id})
        self.assertEqual(request.maintenance_cost, 500.0)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def test_history_is_preserved(self):
        new = self._request()
        new.unlink()  # an untouched new request may be deleted
        # The accounting test base disables tracking; enable it to check the chatter history.
        request = self._request(user_id=self.technician.id).with_context(tracking_disable=False, mail_notrack=False)
        request.stage_id = self.stage_progress
        with self.assertRaises(UserError):
            request.unlink()
        request.stage_id = self.stage_done
        request.archive = True
        self.assertIn(request, self.flat.maintenance_ids, "Archived requests stay in the property's history")
        found = self.env['maintenance.request'].search(self.flat.action_view_maintenance_requests()['domain'])
        self.assertIn(request, found)
        self.env.flush_all()  # tracking values are written when changes are flushed
        self.cr.flush()
        tracked = request.message_ids.tracking_value_ids.field_id.mapped('name')
        self.assertIn('stage_id', tracked, "Status changes are tracked in the chatter")

    def test_property_with_maintenance_cannot_lose_it(self):
        self._request(property_id=self.other_flat.id)
        with self.assertRaises(UserError):
            self.other_flat.unlink()

    # ------------------------------------------------------------------
    # Costs
    # ------------------------------------------------------------------
    def test_charge_cost_to_tenant(self):
        request = self._request(maintenance_cost=1200.0, cost_charged_to='tenant', rental_contract_id=self.lease.id)
        with self.assertRaises(AccessError):
            request.with_user(self.agent).action_charge_cost()
        action = request.with_user(self.accountant).action_charge_cost()
        invoice = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.state, 'draft')
        self.assertEqual(invoice.partner_id, self.tenant)
        self.assertEqual(invoice.maintenance_request_id, request)
        self.assertEqual(invoice.property_id, self.flat)
        self.assertEqual(invoice.property_rental_contract_id, self.lease)
        self.assertEqual(invoice.amount_untaxed, 1200.0)
        self.assertEqual(invoice.invoice_line_ids.product_id, self.env.ref('inom_rental_management_maintenance.product_maintenance_recharge'))
        self.assertEqual(request.recharge_move_count, 1)
        with self.assertRaises(UserError):
            request.action_charge_cost()  # no second invoice
        with self.assertRaises(UserError):
            request.write({'maintenance_cost': 1500.0})  # cost locked once invoiced
        self.assertNotIn(invoice, self.env['account.move'].search([('property_rental_move_kind', '=', 'rent')]),
                         "A maintenance recharge is not rent")
        invoice.button_cancel()
        request.write({'maintenance_cost': 1500.0})
        request.action_charge_cost()
        self.assertEqual(request.recharge_move_count, 1)

    def test_charge_cost_to_owner_and_company(self):
        request = self._request(maintenance_cost=800.0, cost_charged_to='owner')
        invoice = self.env['account.move'].browse(request.action_charge_cost()['res_id'])
        self.assertEqual(invoice.partner_id, self.owner)
        company_cost = self._request(maintenance_cost=300.0)
        with self.assertRaises(UserError):
            company_cost.action_charge_cost()
        with self.assertRaises(ValidationError):
            self._request(maintenance_cost=10.0, cost_charged_to='tenant')  # no lease linked

    # ------------------------------------------------------------------
    # Notifications and summary report
    # ------------------------------------------------------------------
    def test_scheduled_maintenance_reminder(self):
        from dateutil.relativedelta import relativedelta
        soon = fields.Datetime.now() + relativedelta(hours=12)
        request = self._request(user_id=self.technician.id, schedule_date=soon)
        later = self._request(name='Annual check', user_id=self.technician.id,
                              schedule_date=fields.Datetime.now() + relativedelta(days=10))
        unassigned = self._request(name='Nobody', user_id=False, schedule_date=soon)
        todo = self.env.ref('mail.mail_activity_data_todo')

        def reminders(req):
            return req.activity_ids.filtered(lambda a: a.activity_type_id == todo and 'Scheduled maintenance' in a.summary)

        Notification = self.env['property.notification']
        Notification._cron_send_notifications()
        Notification._cron_send_notifications()
        self.assertEqual(len(reminders(request)), 1, "One reminder, not one per run")
        self.assertEqual(reminders(request).user_id, self.technician)
        self.assertFalse(reminders(later), "Work scheduled later is not reminded yet")
        self.assertFalse(reminders(unassigned))
        # Rescheduling within the window reminds again; finished work is not reminded.
        request.schedule_date = soon + relativedelta(hours=2)
        Notification._cron_send_notifications()
        self.assertEqual(len(reminders(request)), 2)
        request.stage_id = self.stage_done
        request.schedule_date = soon + relativedelta(hours=3)
        Notification._cron_send_notifications()
        self.assertEqual(len(reminders(request)), 2)

    def test_maintenance_summary_report(self):
        from odoo.tools.safe_eval import safe_eval
        self._request(maintenance_cost=100.0)
        self._request(name='Paint', maintenance_cost=250.0, property_id=self.other_flat.id)
        self.env['maintenance.request'].create({'name': 'Office printer', 'maintenance_team_id': self.team.id})
        action = self.env.ref('inom_rental_management_maintenance.action_report_maintenance_summary')
        groups = dict(self.env['maintenance.request']._read_group(
            safe_eval(action.domain), ['property_id'], ['maintenance_cost:sum']))
        self.assertEqual(groups, {self.flat: 100.0, self.other_flat: 250.0}, "Only property requests, costs summed per property")

    def test_dashboard_calendar_shows_scheduled_maintenance(self):
        when = fields.Datetime.now() + relativedelta(days=3)
        request = self._request(schedule_date=when)
        self._request(name='Office printer', property_id=False, schedule_date=when)
        Dashboard = self.env['property.dashboard']
        events = Dashboard._calendar_extra_events(
            self.env(su=True), self.env.company, fields.Date.today(), fields.Date.today() + relativedelta(days=30))
        maintenance = [e for e in events if e['kind'] == 'maintenance']
        self.assertEqual(len(maintenance), 1, "Only property requests, one entry per day")
        self.assertEqual(self.env['maintenance.request'].search(maintenance[0]['action']['domain']), request)
        self.assertEqual(maintenance[0]['badge'], 'Scheduled')

    def test_demo_team_assignment_fills_only_empty_teams(self):
        """ The demo team is assigned by code, so that it also applies when demo data reaches an
        existing database through an upgrade; properties that already have a team keep it. """
        team = self.env.ref('inom_rental_management_maintenance.demo_team_property_care', raise_if_not_found=False)
        if not team:
            team = self.env['maintenance.team'].create({'name': 'Property Care Team test'})
            self.env['ir.model.data'].create({
                'module': 'inom_rental_management_maintenance', 'name': 'demo_team_property_care',
                'model': 'maintenance.team', 'res_id': team.id,
            })
        team.sudo().company_id = self.flat.company_id  # the demo team belongs to the main company
        for name, prop in (('flat', self.flat), ('other', self.other_flat)):
            self.env['ir.model.data'].create({
                'module': 'rm_maintenance_test', 'name': name, 'model': 'property.property', 'res_id': prop.id,
            })
        self.flat.write({'maintenance_team_id': False, 'technician_user_id': False})
        self.other_flat.maintenance_team_id = self.team
        demo = {'rm_maintenance_test.flat': 'base.user_admin', 'rm_maintenance_test.other': False}
        with patch.dict(maintenance_demo.DEMO_TEAM_PROPERTIES, demo, clear=True):
            self.env['property.rental.demo']._load_maintenance_demo()
        self.assertEqual(self.flat.maintenance_team_id, team)
        self.assertEqual(self.flat.technician_user_id, self.env.ref('base.user_admin'))
        self.assertEqual(self.other_flat.maintenance_team_id, self.team, "An existing team is kept")
