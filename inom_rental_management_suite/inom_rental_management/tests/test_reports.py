from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestReportsDashboard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        cls.env.user.group_ids += cls.env.ref('inom_rental_management.group_rental_admin') \
            + cls.env.ref('sales_team.group_sale_salesman_all_leads')
        cls.agent = new_test_user(cls.env, 'p11_agent', groups='inom_rental_management.group_rental_agent,sales_team.group_sale_salesman')
        cls.manager = new_test_user(cls.env, 'p11_manager', groups='inom_rental_management.group_rental_manager')
        cls.accountant = new_test_user(cls.env, 'p11_accountant', groups='inom_rental_management.group_rental_accountant')
        for user in (cls.agent, cls.manager, cls.accountant):
            user.write({'company_id': company.id, 'company_ids': [Command.set(company.ids)]})

        cls.today = fields.Date.context_today(cls.env.user)
        cls.ptype = cls.env['property.type'].create({'name': 'Flat P11', 'category': 'residential'})
        cls.owner = cls.env['res.partner'].create({'name': 'P11 Owner', 'is_property_owner': True})
        cls.owner_2 = cls.env['res.partner'].create({'name': 'P11 Owner 2', 'is_property_owner': True})
        cls.tenant = cls.env['res.partner'].create({'name': 'P11 Tenant', 'is_tenant': True,
                                                    'property_payment_term_id': cls.pay_terms_a.id})
        cls.buyer = cls.env['res.partner'].create({'name': 'P11 Buyer', 'is_property_buyer': True})

        def prop(name, **vals):
            values = {'name': name, 'type_id': cls.ptype.id, 'owner_id': cls.owner.id, 'rent_price': 10000.0,
                      'user_id': cls.agent.id}
            values.update(vals)
            return cls.env['property.property'].create(values)

        cls.available = prop('P11 Available')
        cls.available.action_set_available()
        cls.draft = prop('P11 Draft')
        cls.rented = prop('P11 Rented', owner_id=cls.owner_2.id)
        cls.expiring_prop = prop('P11 Expiring')
        cls.for_sale = prop('P11 For Sale', property_for='sale', sale_price=500000.0, rent_price=0.0)
        cls.for_sale.action_set_available()
        cls.sold_prop = prop('P11 Sold', property_for='sale', sale_price=800000.0, rent_price=0.0)

        cls.lease = cls._make_lease(cls.rented, cls.today - relativedelta(months=2),
                                    cls.today + relativedelta(months=10))
        cls.expiring = cls._make_lease(cls.expiring_prop, cls.today - relativedelta(months=11),
                                       cls.today + relativedelta(days=10))
        cls.lease.action_create_due_invoices()
        cls.invoices = cls.lease.rental_move_ids.filtered(lambda m: m.property_rental_move_kind == 'rent').sorted('invoice_date')
        cls.invoices.action_post()
        cls.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=cls.invoices[0].ids,
        ).create({'payment_date': cls.today}).action_create_payments()

        sale = cls.env['property.sale.contract'].create({'property_id': cls.sold_prop.id, 'buyer_id': cls.buyer.id})
        sale.action_book()
        sale.action_create_balance_invoice()
        sale.invoice_ids.action_post()
        sale.action_sell()
        cls.sale = sale

    @classmethod
    def _make_lease(cls, prop, start, end):
        lease = cls.env['property.rental.contract'].create({
            'property_id': prop.id, 'tenant_id': cls.tenant.id, 'user_id': cls.agent.id,
            'date_start': start, 'date_end': end,
        })
        lease.action_start()
        return lease

    def _dashboard(self, user=None, period='this_month'):
        Dashboard = self.env['property.dashboard']
        data = (Dashboard.with_user(user) if user else Dashboard).get_dashboard_data(period)
        return {tile['key']: tile for section in data['tiles'].values() for tile in section}, data

    # ------------------------------------------------------------------
    # Dashboard figures against the underlying records
    # ------------------------------------------------------------------
    def test_property_and_lease_tiles(self):
        tiles, _data = self._dashboard()
        Property = self.env['property.property']
        company = [('company_id', '=', self.env.company.id)]
        self.assertEqual(tiles['total']['value'], Property.search_count(company))
        self.assertEqual(tiles['available']['value'], Property.search_count(company + [('state', '=', 'available')]))
        self.assertEqual(tiles['for_sale']['value'], Property.search_count(company + [('property_for', '=', 'sale')]))
        self.assertEqual(tiles['for_rent']['value'], Property.search_count(company + [('property_for', '=', 'rent')]))
        self.assertEqual(tiles['occupied']['value'], 2)  # rented and expiring_prop
        self.assertEqual(tiles['vacant']['value'], 2)  # available and draft
        self.assertEqual(tiles['active_contracts']['value'], 2)
        self.assertEqual(tiles['expiring']['value'], 1, "Only the lease ending within 30 days")
        lines = self.env['property.rent.schedule'].search([
            ('company_id', '=', self.env.company.id), ('date_due', '>=', self.today),
            ('date_due', '<=', self.today + relativedelta(days=30)), ('state', '!=', 'paid'), ('state', '!=', 'cancelled'),
        ])
        self.assertAlmostEqual(tiles['upcoming_due']['raw'], sum(lines.mapped('amount')))
        # Each tile opens the matching records.
        action = tiles['occupied']['action']
        self.assertEqual(self.env[action['res_model']].search(action['domain']), self.rented | self.expiring_prop)

    def test_income_tiles_distinguish_invoiced_from_collected(self):
        tiles, data = self._dashboard(period='this_year')
        date_from, date_to = fields.Date.from_string(data['date_from']), fields.Date.from_string(data['date_to'])
        expected_invoiced = sum(m.amount_untaxed_signed for m in self.invoices if date_from <= m.invoice_date <= date_to)
        self.assertAlmostEqual(tiles['rent_invoiced']['raw'], expected_invoiced)
        # Only the first invoice was paid, today.
        self.assertAlmostEqual(tiles['rent_collected']['raw'], self.invoices[0].amount_total)
        self.assertNotEqual(tiles['rent_invoiced']['raw'], tiles['rent_collected']['raw'])
        overdue = self.invoices.filtered(lambda m: m.invoice_date_due < self.today and m.amount_residual)
        self.assertAlmostEqual(tiles['overdue']['raw'], sum(overdue.mapped('amount_residual_signed')))
        self.assertEqual(tiles['sold']['value'], 1)
        self.assertEqual(tiles['sold']['raw_value'], 800000.0)

    def test_date_filters(self):
        tiles, data = self._dashboard(period='last_month')
        date_from = fields.Date.from_string(data['date_from'])
        self.assertEqual(date_from, (self.today.replace(day=1) - relativedelta(months=1)))
        expected = sum(m.amount_untaxed_signed for m in self.invoices
                       if date_from <= m.invoice_date <= fields.Date.from_string(data['date_to']))
        self.assertAlmostEqual(tiles['rent_invoiced']['raw'], expected)
        self.assertEqual(tiles['rent_collected']['raw'], 0.0, "The payment was made this month")
        self.assertEqual(tiles['sold']['value'], 0)
        tiles, _ = self._dashboard(period='this_month')
        self.assertAlmostEqual(tiles['rent_collected']['raw'], self.invoices[0].amount_total)
        # An unknown period falls back to this month.
        _tiles, data = self._dashboard(period='drop table')
        self.assertEqual(data['period'], 'this_month')

    def test_company_filter(self):
        company_2 = self.setup_other_company()['company']
        self.env.user.company_ids |= company_2
        owner = self.env['res.partner'].create({'name': 'Owner C2 P11', 'is_property_owner': True, 'company_id': company_2.id})
        self.env['property.property'].create({'name': 'C2 flat', 'type_id': self.ptype.id, 'owner_id': owner.id,
                                              'company_id': company_2.id})
        one_data = self.env['property.dashboard'].with_context(
            allowed_company_ids=[self.env.company.id],
        ).get_dashboard_data('this_month')
        one = {t['key']: t for section in one_data['tiles'].values() for t in section}
        both = self.env['property.dashboard'].with_context(
            allowed_company_ids=[self.env.company.id, company_2.id],
        ).get_dashboard_data('this_month')
        both_tiles = {t['key']: t for s in both['tiles'].values() for t in s}
        self.assertEqual(both_tiles['total']['value'], one['total']['value'] + 1)

    def test_dashboard_access(self):
        with self.assertRaises(AccessError):
            self._dashboard(user=self.agent)
        tiles, _ = self._dashboard(user=self.manager)
        self.assertIn('rent_invoiced', tiles, "Managers see income figures")
        self.assertFalse(tiles['rent_invoiced']['action'], "but cannot open invoices without Invoicing access")
        tiles, _ = self._dashboard(user=self.accountant)
        self.assertTrue(tiles['rent_invoiced']['action'])

    def test_recent_activity(self):
        _tiles, data = self._dashboard()
        activity = data['lists']['activity']
        self.assertLessEqual(len(activity), 6)
        self.assertEqual([e['when'] for e in activity], sorted((e['when'] for e in activity), reverse=True))
        _tiles, data = self._dashboard(user=self.manager)
        payments = [e for e in data['lists']['activity'] if e['kind'] == 'payment']
        self.assertTrue(all(not e['action'] for e in payments), "No invoice links without Invoicing access")
        kinds = {e['kind'] for e in self.env['property.dashboard']._recent_activity(
            self.env(su=True), self.env.company, lambda amount: str(amount), limit=50)}
        self.assertTrue({'property', 'lease', 'payment', 'sale'} <= kinds)

    def test_calendar_quick_actions_and_chart_range(self):
        _tiles, data = self._dashboard()
        calendar = data['calendar']
        self.assertLessEqual(len(calendar), 4)
        self.assertEqual([e['date'] for e in calendar], sorted(e['date'] for e in calendar))
        self.assertIn('lease', {e['kind'] for e in calendar}, "The lease ending within 30 days is on the calendar")
        for event in calendar:
            self.assertTrue(self.env[event['action']['res_model']].search(event['action']['domain']))
        self.assertEqual(len(data['charts']['income']), 6)
        data = self.env['property.dashboard'].get_dashboard_data('this_month', 'last_30_days')
        self.assertEqual(len(data['charts']['income']), 30)
        self.assertEqual(len(self.env['property.dashboard'].get_dashboard_data('this_month', 'last_12_months')['charts']['income']), 12)
        keys = lambda user: {a['key'] for a in self._dashboard(user=user)[1]['quick_actions']}
        self.assertNotIn('payment', keys(self.manager), "Record Payment needs Invoicing access")
        self.assertIn('payment', keys(self.accountant))
        self.assertNotIn('property', keys(self.accountant), "Accountants cannot create properties")

    def test_dashboard_query_count_does_not_grow(self):
        def count_queries():
            self.env.flush_all()  # pending writes of the records just created are not dashboard queries
            self.env.invalidate_all()
            before = self.cr.sql_log_count
            self._dashboard()
            return self.cr.sql_log_count - before

        count_queries()  # the first call also loads one-off caches (currency, language)
        baseline = count_queries()
        for index in range(15):
            extra = self.env['property.property'].create({
                'name': f'P11 bulk {index}', 'type_id': self.ptype.id, 'owner_id': self.owner.id, 'rent_price': 1000.0,
            })
            if index % 3 == 0:
                self._make_lease(extra, self.today - relativedelta(months=1), self.today + relativedelta(months=6))
        self.assertEqual(count_queries(), baseline, "Dashboard queries do not depend on the number of records")
        self.assertLessEqual(baseline, 30)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def test_rental_income_report_matches_accounting(self):
        Report = self.env['property.rent.invoice.report']
        lines = Report.search([('contract_id', '=', self.lease.id)])
        self.assertEqual(lines.move_id, self.invoices)
        for line in lines:
            move = line.move_id
            self.assertAlmostEqual(line.amount_invoiced, move.amount_untaxed_signed)
            self.assertAlmostEqual(line.amount_paid, move.amount_total_signed - move.amount_residual_signed)
            self.assertAlmostEqual(line.amount_due, move.amount_residual_signed)
            self.assertEqual(line.property_id, self.rented)
            self.assertEqual(line.owner_id, self.owner_2)
            self.assertEqual(line.tenant_id, self.tenant)
            self.assertEqual(line.is_overdue, bool(move.amount_residual and move.invoice_date_due < self.today))

        by_owner = dict((owner, amount) for owner, amount in Report._read_group(
            [('company_id', '=', self.env.company.id)], ['owner_id'], ['amount_invoiced:sum']))
        expected_owner_2 = sum(self.env['account.move'].search([
            ('property_rental_move_kind', '=', 'rent'), ('state', '=', 'posted'), ('property_id.owner_id', '=', self.owner_2.id),
        ]).mapped('amount_untaxed_signed'))
        self.assertAlmostEqual(by_owner[self.owner_2], expected_owner_2)

        outstanding = Report.search([('amount_due', '>', 0), ('tenant_id', '=', self.tenant.id)])
        self.assertEqual(outstanding.move_id, self.invoices.filtered('amount_residual'))
        self.assertNotIn(self.sale.invoice_ids, lines.move_id, "Sale invoices are not rental income")

    def test_report_date_filter_and_credit_notes(self):
        Report = self.env['property.rent.invoice.report']
        first = self.invoices[0]
        dated = Report.search([('invoice_date', '>=', first.invoice_date), ('invoice_date', '<=', first.invoice_date)])
        self.assertIn(first, dated.move_id)
        self.assertTrue(all(line.invoice_date == first.invoice_date for line in dated))
        credit_note = self.invoices[1]._reverse_moves(cancel=True)
        total = sum(Report.search([('contract_id', '=', self.lease.id)]).mapped('amount_invoiced'))
        self.assertAlmostEqual(total, self.lease.rent_invoiced, msg="Credit notes are deducted, as on the lease")
        self.assertIn(credit_note, Report.search([('contract_id', '=', self.lease.id)]).move_id)

    def test_report_access(self):
        with self.assertRaises(AccessError):
            self.env['property.rent.invoice.report'].with_user(self.agent).search([])
        self.assertTrue(self.env['property.rent.invoice.report'].with_user(self.manager).search([]))
        self.assertTrue(self.env['property.rent.invoice.report'].with_user(self.accountant).search([]))

    def test_report_actions(self):
        expiry = self.env.ref('inom_rental_management.action_report_contract_expiry')
        self.assertIn(self.expiring, self.env['property.rental.contract'].search(safe_eval(expiry.domain)))
        occupancy = self.env.ref('inom_rental_management.action_report_occupancy')
        rent_props = self.env['property.property'].search(safe_eval(occupancy.domain))
        self.assertNotIn(self.for_sale, rent_props)
        self.assertIn(self.rented, rent_props)
        sales = self.env.ref('inom_rental_management.action_report_sale_transactions')
        self.assertIn(self.sale, self.env['property.sale.contract'].search(safe_eval(sales.domain)))

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _activities(self, record):
        return record.activity_ids.filtered(lambda a: a.activity_type_id == self.env.ref('mail.mail_activity_data_todo'))

    def test_rent_due_and_overdue_notifications_are_not_duplicated(self):
        soon_prop = self.env['property.property'].create({
            'name': 'P11 Starting soon', 'type_id': self.ptype.id, 'owner_id': self.owner.id, 'rent_price': 7000.0,
            'user_id': self.agent.id,
        })
        soon = self._make_lease(soon_prop, self.today + relativedelta(days=2), self.today + relativedelta(years=1))
        before_lease = len(self._activities(self.lease))
        Notification = self.env['property.notification']
        Notification._cron_send_notifications()
        due_activity = self._activities(soon).filtered(lambda a: 'Rent due' in a.summary)
        self.assertEqual(len(due_activity), 1)
        self.assertEqual(due_activity.user_id, self.agent)
        overdue = self.invoices.filtered(lambda m: m.invoice_date_due < self.today and m.amount_residual)
        overdue_activities = self._activities(self.lease).filtered(lambda a: 'Overdue rent' in a.summary)
        self.assertEqual(len(overdue_activities), len(overdue))
        Notification._cron_send_notifications()
        Notification._cron_send_notifications()
        self.assertEqual(len(self._activities(soon).filtered(lambda a: 'Rent due' in a.summary)), 1)
        # The lease also has a period due today and unpaid: it gets one rent due reminder, once.
        lease_activities = self._activities(self.lease)
        self.assertEqual(len(lease_activities.filtered(lambda a: 'Overdue rent' in a.summary)), len(overdue))
        self.assertEqual(len(lease_activities.filtered(lambda a: 'Rent due' in a.summary)), 1)
        self.assertEqual(len(lease_activities) - before_lease, len(overdue) + 1)

    def test_pending_enquiry_notification(self):
        lead = self.env['crm.lead'].create({
            'name': 'Quiet enquiry', 'type': 'opportunity', 'property_for': 'rent', 'property_id': self.available.id,
            'partner_id': self.tenant.id, 'user_id': self.agent.id,
        })
        lead.activity_ids.unlink()
        Notification = self.env['property.notification']
        Notification._cron_send_notifications()
        self.assertFalse(lead.activity_ids, "Recent enquiries are not chased")
        self.env.flush_all()
        self.env.cr.execute("UPDATE crm_lead SET write_date = %s WHERE id = %s",
                            [fields.Datetime.now() - relativedelta(days=5), lead.id])
        lead.invalidate_recordset()
        Notification._cron_send_notifications()
        self.assertEqual(len(lead.activity_ids), 1)
        self.assertEqual(lead.activity_ids.user_id, self.agent)
        Notification._cron_send_notifications()
        self.assertEqual(len(lead.activity_ids), 1, "No second reminder while one is planned")
