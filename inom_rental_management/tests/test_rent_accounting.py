from datetime import date

from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRentAccounting(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        cls.env.user.group_ids += cls.env.ref('inom_rental_management.group_rental_admin')
        cls.agent = new_test_user(cls.env, 'p7_agent', groups='inom_rental_management.group_rental_agent')
        cls.agent_2 = new_test_user(cls.env, 'p7_agent_2', groups='inom_rental_management.group_rental_agent')
        cls.accountant = new_test_user(cls.env, 'p7_accountant', groups='inom_rental_management.group_rental_accountant')
        for user in (cls.agent, cls.agent_2, cls.accountant):
            user.write({'company_id': company.id, 'company_ids': [Command.set(company.ids)]})

        # Deposits go to a liability account: configured by the company, not by the module.
        cls.deposit_account = cls.env['account.account'].create({
            'name': 'Tenant Deposits Held', 'code': 'TDH001', 'account_type': 'liability_current',
        })
        cls.rent_product = cls.env.ref('inom_rental_management.product_rent')
        cls.deposit_product = cls.env.ref('inom_rental_management.product_security_deposit')
        cls.deduction_product = cls.env.ref('inom_rental_management.product_deposit_deduction')
        cls.deposit_product.property_account_income_id = cls.deposit_account

        cls.property_type = cls.env['property.type'].create({'name': 'Flat P7', 'category': 'residential'})
        cls.owner = cls.env['res.partner'].create({'name': 'P7 Owner', 'is_property_owner': True})
        cls.tenant = cls.env['res.partner'].create({'name': 'P7 Tenant', 'is_tenant': True})
        cls.flat = cls.env['property.property'].create({
            'name': 'Skyline D-401', 'type_id': cls.property_type.id, 'owner_id': cls.owner.id,
            'rent_price': 10000.0, 'user_id': cls.agent.id,
        })
        cls.today = fields.Date.context_today(cls.env.user)

    def _lease(self, start=None, end=None, **kwargs):
        start = start or self.today - relativedelta(months=2)
        vals = {
            'property_id': kwargs.pop('property_id', self.flat.id), 'tenant_id': self.tenant.id,
            'user_id': self.agent.id, 'date_start': start, 'date_end': end or start + relativedelta(years=1, days=-1),
            'deposit_amount': 30000.0,
        }
        vals.update(kwargs)
        lease = self.env['property.rental.contract'].create(vals)
        lease.action_start()
        return lease

    def _invoices(self, lease, kind='rent'):
        return lease.rental_move_ids.filtered(lambda m: m.property_rental_move_kind == kind)

    def _pay(self, moves, amount=None):
        vals = {'amount': amount} if amount else {}
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=moves.ids,
        ).create(vals).action_create_payments()

    # ------------------------------------------------------------------
    # Billing schedule
    # ------------------------------------------------------------------
    def test_schedule_follows_payment_frequency(self):
        start = date(2026, 1, 1)
        expected = {'monthly': (12, 10000.0), 'quarterly': (4, 30000.0), 'half_yearly': (2, 60000.0), 'yearly': (1, 120000.0)}
        for frequency, (count, amount) in expected.items():
            with self.subTest(frequency=frequency):
                prop = self.flat.copy({'name': f'Flat {frequency}'})
                lease = self._lease(start, date(2026, 12, 31), property_id=prop.id, rent_period=frequency)
                lines = lease.rent_schedule_ids
                self.assertEqual(len(lines), count)
                self.assertEqual(set(lines.mapped('amount')), {amount})
                self.assertEqual(lines[0].period_start, start)
                self.assertEqual(lines[-1].period_end, date(2026, 12, 31))
                self.assertEqual(lines.mapped('date_due'), lines.mapped('period_start'), "Rent is due in advance")
                self.assertEqual(sum(lines.mapped('amount')), 120000.0)

    def test_schedule_prorates_last_period(self):
        lease = self._lease(date(2026, 1, 1), date(2026, 2, 15))
        jan, feb = lease.rent_schedule_ids
        self.assertEqual(jan.amount, 10000.0)
        self.assertEqual((feb.period_start, feb.period_end), (date(2026, 2, 1), date(2026, 2, 15)))
        self.assertEqual(feb.amount, round(10000.0 * 15 / 28, 2))

    def test_schedule_invoice_from(self):
        lease = self._lease(date(2026, 1, 1), date(2026, 12, 31), invoice_from=date(2026, 7, 1))
        self.assertEqual(lease.rent_schedule_ids[0].period_start, date(2026, 7, 1))
        self.assertEqual(len(lease.rent_schedule_ids), 6)

    def test_schedule_only_for_started_leases(self):
        draft = self.env['property.rental.contract'].create({
            'property_id': self.flat.id, 'tenant_id': self.tenant.id,
            'date_start': date(2030, 1, 1), 'date_end': date(2030, 12, 31),
        })
        self.assertFalse(draft.rent_schedule_ids)
        draft.action_start()
        self.assertEqual(len(draft.rent_schedule_ids), 12)
        draft.sudo()._generate_rent_schedule()
        self.assertEqual(len(draft.rent_schedule_ids), 12, "The schedule is never generated twice")

    def test_legacy_lease_schedule(self):
        lease = self._lease(date(2025, 1, 1), date(2026, 12, 31))
        lease.rent_schedule_ids.sudo().unlink()  # as for a lease started before rent invoicing existed
        with self.assertRaises(AccessError):
            lease.with_user(self.agent).action_generate_rent_schedule()
        lease.action_generate_rent_schedule()
        self.assertEqual(len(lease.rent_schedule_ids), 24)
        with self.assertRaises(UserError):
            lease.action_generate_rent_schedule()

    # ------------------------------------------------------------------
    # Invoice generation
    # ------------------------------------------------------------------
    def test_scheduled_job_is_idempotent(self):
        lease = self._lease()  # started two months ago: three periods are due
        Schedule = self.env['property.rent.schedule']
        Schedule._cron_generate_rent_invoices()
        invoices = self._invoices(lease)
        self.assertEqual(len(invoices), 3)
        Schedule._cron_generate_rent_invoices()
        Schedule._cron_generate_rent_invoices()
        self.assertEqual(self._invoices(lease), invoices, "Running the job again creates nothing")
        self.assertEqual(lease.rent_schedule_ids.filtered(lambda l: l.move_id).mapped('move_id'), invoices)

        invoice = invoices.sorted('invoice_date')[0]
        line = lease.rent_schedule_ids[0]
        self.assertEqual(invoice.state, 'draft', "Invoices are not posted without explicit configuration")
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.partner_id, self.tenant)
        self.assertEqual(invoice.property_id, self.flat)
        self.assertEqual(invoice.property_rental_contract_id, lease)
        self.assertEqual(invoice.property_rent_schedule_id, line)
        self.assertEqual(invoice.invoice_date, line.date_due)
        self.assertEqual(invoice.invoice_line_ids.product_id, self.rent_product)
        self.assertEqual(invoice.amount_untaxed, 10000.0)
        self.assertEqual(invoice.journal_id.type, 'sale')
        self.assertEqual(line.state, 'draft')

        # Manual invoicing of due rent also skips what is already invoiced.
        with self.assertRaises(UserError):
            lease.action_create_due_invoices()

    def test_advance_days(self):
        lease = self._lease()
        self.env.company.rental_invoice_advance_days = 40
        self.env['property.rent.schedule']._cron_generate_rent_invoices()
        self.assertEqual(len(self._invoices(lease)), 4)

    def test_database_rejects_a_second_invoice_for_a_period(self):
        lease = self._lease()
        line = lease.rent_schedule_ids[0]
        line._create_invoices()
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.env['account.move'].create(line._prepare_invoice_vals())
            self.env.flush_all()
        self.assertEqual(len(line.move_ids), 1)

    def test_auto_post_setting(self):
        self.env.company.rental_auto_post_invoices = True
        lease = self._lease()
        lease.action_create_due_invoices()
        self.assertEqual(set(self._invoices(lease).mapped('state')), {'posted'})
        self.assertEqual(lease.rent_schedule_ids[0].state, 'invoiced')

    def test_taxes_journal_and_fiscal_position(self):
        self.rent_product.taxes_id = self.tax_sale_a
        journal = self.company_data['default_journal_sale'].copy({'name': 'Rent Journal', 'code': 'RENT'})
        self.env.company.rental_journal_id = journal
        lease = self._lease()
        lease.rent_schedule_ids[0]._create_invoices()
        invoice = self._invoices(lease)
        self.assertEqual(invoice.journal_id, journal)
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_a)
        self.assertEqual(invoice.amount_untaxed, 10000.0)
        self.assertGreater(invoice.amount_total, 10000.0)

        self.tenant.property_account_position_id = self.fiscal_pos_a
        lease.rent_schedule_ids[1]._create_invoices()
        mapped = self._invoices(lease) - invoice
        self.assertEqual(mapped.fiscal_position_id, self.fiscal_pos_a)
        self.assertEqual(mapped.invoice_line_ids.tax_ids, self.tax_sale_b)

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------
    def test_cancel_draft_invoice(self):
        lease = self._lease()
        line = lease.rent_schedule_ids[0]
        line._create_invoices()
        invoice = line.move_id
        try:  # a period's invoice is cancelled, never deleted
            with mute_logger('odoo.sql_db'), self.env.cr.savepoint():
                invoice.unlink()
                self.env.flush_all()
        except (UserError, IntegrityError):
            pass
        else:
            self.fail("The invoice of a rental period was deleted")
        invoice.button_cancel()
        self.assertEqual(line.state, 'cancelled')
        self.env['property.rent.schedule']._cron_generate_rent_invoices()
        self.assertEqual(line.move_id, invoice, "The job does not re-invoice a cancelled period")
        line.action_create_invoice()
        self.assertNotEqual(line.move_id, invoice)
        self.assertEqual(line.state, 'draft')
        self.assertEqual(len(line.move_ids), 2, "The cancelled invoice stays in the period's history")

    def test_credit_posted_invoice(self):
        lease = self._lease()
        line = lease.rent_schedule_ids[0]
        line._create_invoices()
        invoice = line.move_id
        invoice.action_post()
        self.assertEqual(lease.rent_invoiced, 10000.0)
        credit_note = invoice._reverse_moves(cancel=True)
        self.assertEqual(credit_note.state, 'posted')
        self.assertEqual(credit_note.property_rent_schedule_id, line, "The credit note stays linked to the period")
        self.assertEqual(invoice.payment_state, 'reversed')
        self.assertEqual(line.state, 'cancelled')
        self.assertEqual(lease.rent_invoiced, 0.0)
        line.action_create_invoice()  # re-invoicing a credited period is allowed
        self.assertEqual(line.state, 'draft')

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------
    def test_payments_and_reconciliation(self):
        lease = self._lease()
        lease.action_create_due_invoices()
        invoices = self._invoices(lease).sorted('invoice_date')
        invoices.action_post()
        self.assertEqual(lease.rent_invoiced, 30000.0)
        self.assertEqual(lease.rent_received, 0.0, "Invoiced is not collected")
        self.assertEqual(lease.rent_due, 30000.0)

        self._pay(invoices[0])
        self._pay(invoices[1], amount=4000.0)
        self.assertEqual(lease.rent_received, 14000.0)
        self.assertEqual(lease.rent_due, 16000.0)
        lines = lease.rent_schedule_ids.sorted('period_start')
        self.assertIn(lines[0].state, ('paid',))
        self.assertEqual(lines[1].state, 'invoiced')
        self.assertEqual(lines[1].amount_residual, 6000.0)

        payments = self.env['account.payment'].search(lease.action_view_payments()['domain'])
        self.assertEqual(len(payments), 2)
        self.assertEqual(set(invoices._get_reconciled_payments().ids), set(payments.ids))

    def test_overdue_rent(self):
        self.tenant.property_payment_term_id = self.pay_terms_a  # immediate payment
        lease = self._lease()
        lease.action_create_due_invoices()
        invoices = self._invoices(lease).sorted('invoice_date')
        invoices.action_post()
        # Immediate payment terms: invoices dated in the past are overdue.
        late = invoices.filtered(lambda m: m.invoice_date_due < self.today)
        self.assertTrue(late)
        self.assertEqual(lease.rent_overdue, sum(late.mapped('amount_residual')))
        overdue_domain = [
            ('invoice_date_due', '<', 'today'), ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')), ('move_type', '!=', 'entry'),
            ('property_rental_move_kind', '=', 'rent'),
        ]
        self.assertEqual(self.env['account.move'].search(overdue_domain) & invoices, late)
        self._pay(late)
        self.assertEqual(lease.rent_overdue, 0.0)

    # ------------------------------------------------------------------
    # Deposits
    # ------------------------------------------------------------------
    def test_deposit_kept_out_of_rental_income(self):
        lease = self._lease()
        lease.action_invoice_deposit()
        deposit_invoice = self._invoices(lease, 'deposit')
        self.assertEqual(deposit_invoice.invoice_line_ids.account_id, self.deposit_account)
        self.assertEqual(deposit_invoice.amount_untaxed, 30000.0)
        self.assertEqual(lease.deposit_state, 'to_invoice', "A draft deposit invoice is not yet invoiced")
        with self.assertRaises(UserError):
            lease.action_invoice_deposit()
        deposit_invoice.action_post()
        self.assertEqual(lease.deposit_state, 'invoiced')
        self.assertEqual(lease.rent_invoiced, 0.0, "Deposits are not rent")
        self._pay(deposit_invoice)
        self.assertEqual(lease.deposit_state, 'held')
        self.assertEqual(lease.deposit_held, 30000.0)

    def test_deposit_refund_with_deduction(self):
        lease = self._lease()
        lease.action_invoice_deposit()
        deposit_invoice = self._invoices(lease, 'deposit')
        deposit_invoice.action_post()
        self._pay(deposit_invoice)
        with self.assertRaises(UserError):
            lease.action_open_deposit_settlement()  # lease still running
        lease.action_close()

        wizard = self.env['property.deposit.settlement'].with_user(self.accountant).with_context(
            default_contract_id=lease.id,
        ).create({'line_ids': [Command.create({'name': 'Broken window', 'amount': 5000.0})]})
        self.assertEqual(wizard.refund_amount, 25000.0)
        action = wizard.action_settle()
        credit_note = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(credit_note.move_type, 'out_refund')
        self.assertEqual(credit_note.state, 'draft', "Settlements are left in draft for review")
        self.assertEqual(credit_note.amount_total, 25000.0)
        deposit_line = credit_note.invoice_line_ids.filtered(lambda l: l.product_id == self.deposit_product)
        deduction_line = credit_note.invoice_line_ids - deposit_line
        self.assertEqual(deposit_line.account_id, self.deposit_account)
        self.assertEqual(deduction_line.account_id, self.deduction_product._get_product_accounts()['income'])
        with self.assertRaises(UserError):
            lease.action_open_deposit_settlement()  # a draft settlement already exists

        credit_note.action_post()
        self.assertEqual(lease.deposit_state, 'settled')
        self.assertEqual(lease.deposit_deducted, 5000.0)
        self.assertEqual(lease.deposit_refunded, 25000.0)
        self.assertEqual(lease.deposit_held, 0.0)
        # The refund is paid out with a standard outgoing payment.
        self._pay(credit_note)
        self.assertIn(credit_note.payment_state, ('paid', 'in_payment'))

    def test_deposit_adjusted_against_unpaid_rent(self):
        lease = self._lease()
        lease.action_invoice_deposit()
        deposit_invoice = self._invoices(lease, 'deposit')
        deposit_invoice.action_post()
        self._pay(deposit_invoice)
        lease.rent_schedule_ids[0]._create_invoices()
        rent_invoice = self._invoices(lease)
        rent_invoice.action_post()
        lease.action_close()
        action = self.env['property.deposit.settlement'].with_context(default_contract_id=lease.id).create({}).action_settle()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_note.action_post()
        # Use the deposit owed to the tenant against the unpaid rent, with standard reconciliation.
        credit_line = credit_note.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        rent_invoice.js_assign_outstanding_line(credit_line.id)
        self.assertTrue(rent_invoice.currency_id.is_zero(rent_invoice.amount_residual))
        self.assertEqual(lease.rent_schedule_ids[0].state, 'paid', "Rent settled by the deposit is paid, not cancelled")
        self.assertEqual(lease.rent_due, 0.0)
        self.assertEqual(credit_note.amount_residual, 20000.0)

    def test_deductions_cannot_exceed_deposit(self):
        lease = self._lease()
        lease.action_invoice_deposit()
        deposit_invoice = self._invoices(lease, 'deposit')
        deposit_invoice.action_post()
        self._pay(deposit_invoice)
        lease.action_close()
        with self.assertRaises(ValidationError):
            self.env['property.deposit.settlement'].with_context(default_contract_id=lease.id).create({
                'line_ids': [Command.create({'name': 'Everything', 'amount': 31000.0})],
            })

    def test_settings_warn_when_deposit_is_income(self):
        settings = self.env['res.config.settings'].create({})
        self.assertFalse(settings.rental_deposit_account_warning)
        self.deposit_product.property_account_income_id = self.company_data['default_account_revenue']
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.rental_deposit_account_warning)

    # ------------------------------------------------------------------
    # Early end
    # ------------------------------------------------------------------
    def test_termination_trims_schedule(self):
        lease = self._lease(date(2026, 1, 1), date(2026, 12, 31))
        lease.rent_schedule_ids.sorted('period_start')[:2]._create_invoices()
        self.env['property.rental.contract.terminate'].create({
            'contract_id': lease.id, 'date_terminated': date(2026, 4, 10), 'termination_reason': 'tenant_request',
        }).action_terminate()
        lines = lease.rent_schedule_ids.sorted('period_start')
        self.assertEqual(len(lines), 4, "Periods after the termination are removed")
        self.assertEqual(lines[-1].period_end, date(2026, 4, 10))
        self.assertEqual(lines[-1].amount, round(10000.0 * 10 / 30, 2))
        self.assertEqual(len(self._invoices(lease)), 2, "Existing invoices are untouched")

    def test_termination_warns_about_invoices_beyond_end(self):
        lease = self._lease(date(2026, 1, 1), date(2026, 12, 31))
        lease.rent_schedule_ids.sorted('period_start')[:6]._create_invoices()
        self.env['property.rental.contract.terminate'].create({
            'contract_id': lease.id, 'date_terminated': date(2026, 3, 31), 'termination_reason': 'mutual',
        }).action_terminate()
        self.assertEqual(len(lease.rent_schedule_ids), 6, "Invoiced periods are kept for the accountant to credit")
        self.assertIn('already invoiced past that date', lease.message_ids[0].body)

    # ------------------------------------------------------------------
    # Permissions and companies
    # ------------------------------------------------------------------
    def test_permissions(self):
        lease = self._lease()
        with self.assertRaises(AccessError):
            lease.with_user(self.agent).action_create_due_invoices()
        with self.assertRaises(UserError):
            lease.rent_schedule_ids[0].with_user(self.agent).action_create_invoice()
        with self.assertRaises(AccessError):
            lease.with_user(self.agent).action_invoice_deposit()
        # The agent sees the schedule and totals of their lease, not another agent's.
        self.assertEqual(len(lease.with_user(self.agent).rent_schedule_ids), 12)
        self.assertEqual(lease.with_user(self.agent).rent_due, 0.0)
        self.assertFalse(self.env['property.rent.schedule'].with_user(self.agent_2).search([('contract_id', '=', lease.id)]))
        with self.assertRaises(AccessError):
            lease.rent_schedule_ids[0].with_user(self.agent).write({'amount': 1.0})
        # The accountant invoices, although they cannot edit the lease.
        lease.with_user(self.accountant).action_create_due_invoices()
        self.assertEqual(len(self._invoices(lease)), 3)

    def test_multi_company(self):
        company_2 = self.setup_other_company()['company']
        self.env.user.company_ids |= company_2
        owner_2 = self.env['res.partner'].create({'name': 'Owner C2', 'is_property_owner': True, 'company_id': company_2.id})
        flat_2 = self.env['property.property'].create({
            'name': 'Company 2 Flat', 'type_id': self.property_type.id, 'owner_id': owner_2.id,
            'rent_price': 500.0, 'company_id': company_2.id,
        })
        lease_1 = self._lease()
        lease_2 = self.env['property.rental.contract'].with_company(company_2).create({
            'property_id': flat_2.id, 'tenant_id': self.tenant.id,
            'date_start': self.today - relativedelta(months=2), 'date_end': self.today + relativedelta(months=10),
        })
        lease_2.with_company(company_2).action_start()
        self.assertEqual(lease_2.rent_schedule_ids.company_id, company_2)

        self.env['property.rent.schedule']._cron_generate_rent_invoices()
        invoices_2 = lease_2.with_company(company_2).rental_move_ids
        self.assertEqual(len(self._invoices(lease_1)), 3)
        self.assertEqual(len(invoices_2), 3)
        self.assertEqual(invoices_2.company_id, company_2)
        self.assertEqual(invoices_2.journal_id.company_id, company_2)
        self.assertEqual(invoices_2.currency_id, company_2.currency_id)
        # Users of the first company do not see the second company's periods.
        self.assertFalse(self.env['property.rent.schedule'].with_user(self.accountant).search([('company_id', '=', company_2.id)]))

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def test_report_actions(self):
        lease = self._lease()
        lease.action_invoice_deposit()
        lease.action_create_due_invoices()
        rent = self._invoices(lease).sorted('invoice_date')
        rent.action_post()
        self._pay(rent[0])

        Schedule = self.env['property.rent.schedule']
        due = Schedule.search([('date_due', '<=', 'today'), ('state', 'in', ('pending', 'draft', 'invoiced')),
                               ('contract_id', '=', lease.id)])
        self.assertEqual(len(due), 2, "Rent due: periods due and not paid")
        paid_action = self.env.ref('inom_rental_management.action_paid_rent')
        paid = self.env['account.move'].search(safe_eval(paid_action.domain) + [
            ('state', '=', 'posted'), ('payment_state', 'in', ('paid', 'in_payment')),
        ])
        self.assertEqual(paid & rent, rent[0])
        outstanding_action = self.env.ref('inom_rental_management.action_outstanding_rent')
        outstanding = self.env['account.move'].search(safe_eval(outstanding_action.domain) + [
            ('payment_state', 'in', ('not_paid', 'partial')),
        ])
        self.assertEqual(outstanding & rent, rent[1:])
        deposit_action = self.env.ref('inom_rental_management.action_deposit_status')
        self.assertIn(lease, self.env['property.rental.contract'].search(safe_eval(deposit_action.domain)))
