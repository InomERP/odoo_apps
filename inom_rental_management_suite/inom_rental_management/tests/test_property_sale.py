from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestPropertySale(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        # The accounting test user also acts as Real Estate administrator and CRM user.
        cls.env.user.group_ids += cls.env.ref('inom_rental_management.group_rental_admin') \
            + cls.env.ref('sales_team.group_sale_salesman')
        cls.agent = new_test_user(cls.env, 'p5_agent', groups='inom_rental_management.group_rental_agent')
        cls.agent_2 = new_test_user(cls.env, 'p5_agent_2', groups='inom_rental_management.group_rental_agent')
        cls.sales_agent = new_test_user(
            cls.env, 'p5_sales_agent',
            groups='inom_rental_management.group_rental_agent,sales_team.group_sale_salesman',
        )
        cls.accountant = new_test_user(cls.env, 'p5_accountant', groups='inom_rental_management.group_rental_accountant')
        cls.billing_manager = new_test_user(
            cls.env, 'p5_billing_manager',
            groups='inom_rental_management.group_rental_manager,account.group_account_invoice',
        )
        for user in (cls.agent, cls.agent_2, cls.sales_agent, cls.accountant, cls.billing_manager):
            user.write({'company_id': company.id, 'company_ids': [Command.set(company.ids)]})

        cls.property_type = cls.env['property.type'].create({'name': 'Villa P5', 'category': 'residential'})
        cls.owner = cls.env['res.partner'].create({'name': 'Seller Owner', 'is_property_owner': True})
        cls.buyer = cls.env['res.partner'].create({'name': 'Karan Desai', 'is_property_buyer': True})
        cls.buyer_2 = cls.env['res.partner'].create({'name': 'Second Buyer', 'is_property_buyer': True})
        cls.villa = cls.env['property.property'].create({
            'name': 'Green Meadows Villa 12', 'type_id': cls.property_type.id, 'property_for': 'sale',
            'owner_id': cls.owner.id, 'sale_price': 5000000.0, 'user_id': cls.agent.id,
        })
        cls.villa.action_set_available()
        cls.booking_product = cls.env.ref('inom_rental_management.product_property_booking')
        cls.sale_product = cls.env.ref('inom_rental_management.product_property_sale')

    def _sale(self, user=None, **kwargs):
        vals = {'property_id': self.villa.id, 'buyer_id': self.buyer.id, 'booking_amount': 500000.0}
        vals.update(kwargs)
        Sale = self.env['property.sale.contract']
        return (Sale.with_user(user) if user else Sale).create(vals)

    def _invoice_fully(self, sale):
        """ Post the booking and balance invoices of a booked sale, as the accountant. """
        sale_acc = sale.with_user(self.accountant)
        if sale.booking_amount:
            sale_acc.action_create_booking_invoice()
        sale_acc.action_create_balance_invoice()
        invoices = sale.with_user(self.env.user).invoice_ids
        invoices.action_post()
        return invoices

    def _pay(self, invoices):
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=invoices.ids,
        ).create({'group_payment': True}).action_create_payments()

    # ------------------------------------------------------------------
    # Sale records and relationships
    # ------------------------------------------------------------------
    def test_create_sale(self):
        sale = self._sale(user=self.agent)
        self.assertTrue(sale.name.startswith('SC/'))
        self.assertEqual(sale.state, 'draft')
        self.assertEqual(sale.property_id, self.villa)
        self.assertEqual(sale.buyer_id, self.buyer)
        self.assertEqual(sale.owner_id, self.owner)
        self.assertEqual(sale.sale_price, 5000000.0, "The agreed price defaults to the listed price")
        self.assertEqual(sale.user_id, self.agent)
        self.assertEqual(sale.invoice_status, 'not_invoiced')
        # A draft sale is an offer: the property stays available.
        self.assertEqual(self.villa.state, 'available')
        self.assertEqual(self.buyer.sale_contract_count, 1)
        self.assertEqual(self.owner.sale_contract_count, 1)
        self.assertEqual(self.villa.sale_contract_count, 1)

    def test_customer_and_property_relationships(self):
        with self.assertRaises(ValidationError):
            self._sale(buyer_id=self.env['res.partner'].create({'name': 'No role'}).id)
        self.owner.is_property_buyer = True
        with self.assertRaises(ValidationError):
            self._sale(buyer_id=self.owner.id)
        rental = self.villa.copy({'property_for': 'rent', 'rent_price': 1000.0})
        with self.assertRaises(ValidationError):
            self._sale(property_id=rental.id)
        with self.assertRaises(ValidationError):
            self._sale(booking_amount=6000000.0)

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------
    def test_full_sale_workflow(self):
        sale = self._sale(user=self.agent)
        sale.with_user(self.agent).action_book()
        self.assertEqual(sale.state, 'booked')
        self.assertEqual(self.villa.state, 'booked', "Booking reserves the property")

        invoices = self._invoice_fully(sale)
        self.assertEqual(sale.invoice_status, 'invoiced')
        sale.with_user(self.agent).action_sell()
        self.assertEqual(sale.state, 'sold')
        self.assertEqual(self.villa.state, 'sold')
        self.assertTrue(sale.date_sold)

        self._pay(invoices)
        self.assertEqual(sale.invoice_status, 'paid')
        self.assertEqual(sale.amount_due, 0.0)

    def test_invalid_transitions(self):
        sale = self._sale()
        with self.assertRaises(UserError):
            sale.action_sell()  # draft -> sold
        with self.assertRaises(UserError):
            sale.action_reset_to_draft()  # draft -> draft
        with self.assertRaises(UserError):
            sale.action_create_booking_invoice()  # invoicing a draft
        sale.action_book()
        with self.assertRaises(UserError):
            sale.action_book()  # booked twice
        with self.assertRaises(UserError):
            sale.action_sell()  # not invoiced yet
        with self.assertRaises(UserError):
            sale.write({'sale_price': 4000000.0})  # agreed price locked once booked
        with self.assertRaises(UserError):
            sale.write({'buyer_id': self.buyer_2.id})
        self._invoice_fully(sale)
        sale.action_sell()
        for method in ('action_cancel', 'action_book', 'action_reset_to_draft', 'action_create_balance_invoice'):
            with self.subTest(method=method), self.assertRaises(UserError):
                getattr(sale, method)()
        self.assertEqual(sale.state, 'sold')

    def test_booking_needs_price_and_free_property(self):
        free_sale = self._sale(sale_price=0.0, booking_amount=0.0)
        with self.assertRaises(UserError):
            free_sale.action_book()
        self.villa.sudo().state = 'rented'
        sale = self._sale()
        with self.assertRaises(UserError):
            sale.action_book()

    def test_conflicting_sales(self):
        first = self._sale(user=self.agent)
        second = self._sale(user=self.agent_2, buyer_id=self.buyer_2.id)
        self.assertEqual(self.villa.sale_contract_count, 2, "Several offers may exist side by side")
        first.with_user(self.agent).action_book()
        with self.assertRaises(UserError):
            second.with_user(self.agent_2).action_book()
        first.with_user(self.agent).action_cancel()
        self.assertEqual(self.villa.state, 'available')
        second.with_user(self.agent_2).action_book()
        self.assertEqual(self.villa.state, 'booked')

    def test_cancel_draft_and_reset(self):
        sale = self._sale()
        sale.action_cancel()
        self.assertEqual(sale.state, 'cancelled')
        self.assertEqual(self.villa.state, 'available')
        sale.action_reset_to_draft()
        self.assertEqual(sale.state, 'draft')

    def test_cancel_restores_previous_property_state(self):
        prelaunch = self.villa.copy({'name': 'Pre-launch Villa 14'})
        self.assertEqual(prelaunch.state, 'draft')
        sale = self._sale(property_id=prelaunch.id)
        sale.action_book()
        self.assertEqual(prelaunch.state, 'booked')
        sale.action_cancel()
        self.assertEqual(prelaunch.state, 'draft')

    # ------------------------------------------------------------------
    # CRM enquiries
    # ------------------------------------------------------------------
    def test_enquiry_is_not_a_sale(self):
        lead = self.env['crm.lead'].with_user(self.sales_agent).create({
            'name': 'Interested in Villa 12', 'type': 'opportunity', 'partner_id': self.buyer_2.id,
            'property_for': 'sale', 'property_id': self.villa.id, 'ask_price': 4500000.0,
        })
        self.assertEqual(lead.listed_price, 5000000.0)
        self.assertEqual(self.villa.state, 'available', "An enquiry does not reserve the property")
        self.assertEqual(self.villa.with_user(self.sales_agent).lead_count, 1)

        action = lead.with_user(self.sales_agent).action_create_property_sale()
        sale = self.env['property.sale.contract'].browse(action['res_id'])
        self.assertEqual(sale.state, 'draft')
        self.assertEqual(sale.lead_id, lead)
        self.assertEqual(sale.buyer_id, self.buyer_2)
        self.assertEqual(self.villa.state, 'available', "A draft sale does not reserve the property")
        self.assertNotEqual(lead.stage_id.is_won, True)
        self.assertEqual(lead.with_user(self.sales_agent).property_sale_contract_count, 1)

        sale.with_user(self.sales_agent).action_book()
        self.assertTrue(lead.active)
        self.assertFalse(lead.stage_id.is_won, "Booking does not win the enquiry")
        self._invoice_fully(sale)
        sale.with_user(self.sales_agent).action_sell()
        self.assertTrue(lead.stage_id.is_won, "A sold sale wins its enquiry")

    def test_enquiry_conversion_needs_customer_and_sale(self):
        lead = self.env['crm.lead'].create({'name': 'No customer', 'property_for': 'sale', 'property_id': self.villa.id})
        with self.assertRaises(UserError):
            lead.action_create_property_sale()
        lead.write({'property_for': 'rent', 'partner_id': self.buyer.id})
        with self.assertRaises(UserError):
            lead.action_create_property_sale()
        newcomer = self.env['res.partner'].create({'name': 'New Customer'})
        lead.write({'property_for': 'sale', 'partner_id': newcomer.id})
        lead.action_create_property_sale()
        self.assertTrue(newcomer.is_property_buyer)

    # ------------------------------------------------------------------
    # Invoicing through standard accounting
    # ------------------------------------------------------------------
    def test_invoice_creation(self):
        sale = self._sale(payment_term_id=self.pay_terms_b.id)
        sale.action_book()
        sale_acc = sale.with_user(self.accountant)

        action = sale_acc.action_create_booking_invoice()
        booking_invoice = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(booking_invoice.move_type, 'out_invoice')
        self.assertEqual(booking_invoice.state, 'draft')
        self.assertEqual(booking_invoice.partner_id, self.buyer)
        self.assertEqual(booking_invoice.company_id, sale.company_id)
        self.assertEqual(booking_invoice.property_sale_contract_id, sale)
        self.assertEqual(booking_invoice.property_id, self.villa)
        self.assertEqual(booking_invoice.invoice_origin, sale.name)
        self.assertEqual(booking_invoice.invoice_line_ids.product_id, self.booking_product)
        self.assertEqual(booking_invoice.amount_untaxed, 500000.0)
        with self.assertRaises(UserError):
            sale_acc.action_create_booking_invoice()  # no second booking invoice

        self.assertEqual(sale.invoice_status, 'not_invoiced', "Draft invoices are not counted as invoiced")
        booking_invoice.action_post()
        self.assertEqual(sale.invoice_status, 'partial')
        self.assertEqual(sale.amount_invoiced, 500000.0)

        action = sale_acc.action_create_balance_invoice()
        balance_invoice = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(balance_invoice.amount_untaxed, 4500000.0)
        self.assertEqual(balance_invoice.invoice_line_ids.product_id, self.sale_product)
        self.assertEqual(balance_invoice.invoice_payment_term_id, self.pay_terms_b)
        with self.assertRaises(UserError):
            sale_acc.action_create_balance_invoice()  # draft balance already covers the price
        balance_invoice.action_post()
        self.assertEqual(sale.invoice_status, 'invoiced')
        self.assertEqual(sale.amount_invoiced, 5000000.0)
        self.assertEqual(sale.invoice_count, 2)

    def test_status_follows_accounting_records(self):
        sale = self._sale()
        sale.action_book()
        invoices = self._invoice_fully(sale)
        self.assertEqual(sale.amount_due, sum(invoices.mapped('amount_residual_signed')))
        self._pay(invoices.filtered(lambda m: m.invoice_line_ids.product_id == self.booking_product))
        self.assertEqual(sale.amount_paid, 500000.0)
        self.assertEqual(sale.invoice_status, 'invoiced')
        # Resetting an invoice to draft in accounting is reflected immediately.
        balance = invoices.filtered(lambda m: m.invoice_line_ids.product_id == self.sale_product)
        balance.button_draft()
        self.assertEqual(sale.invoice_status, 'partial')
        with self.assertRaises(UserError):
            sale.action_sell()

    def test_cancel_with_invoices_creates_credit_notes(self):
        sale = self._sale()
        sale.action_book()
        sale_acc = sale.with_user(self.accountant)
        booking = self.env['account.move'].browse(sale_acc.action_create_booking_invoice()['res_id'])
        booking.action_post()
        balance = self.env['account.move'].browse(sale_acc.action_create_balance_invoice()['res_id'])

        # An agent without Invoicing access cannot cancel a sale that has invoices.
        sale.user_id = self.agent
        with self.assertRaises(UserError):
            sale.with_user(self.agent).action_cancel()

        # The accountant only reads sales; a manager with Invoicing access cancels it.
        with self.assertRaises(AccessError):
            sale.with_user(self.accountant).action_cancel()
        sale.with_user(self.billing_manager).action_cancel()
        self.assertEqual(sale.state, 'cancelled')
        self.assertEqual(self.villa.state, 'available')
        self.assertEqual(balance.state, 'cancel', "Draft invoices are cancelled")
        credit_note = sale.invoice_ids.filtered(lambda m: m.move_type == 'out_refund')
        self.assertEqual(len(credit_note), 1)
        self.assertEqual(credit_note.state, 'draft', "Credit notes are left in draft for review")
        self.assertEqual(credit_note.reversed_entry_id, booking)
        self.assertEqual(credit_note.property_sale_contract_id, sale)
        credit_note.action_post()
        self.assertEqual(sale.amount_invoiced, 0.0)

    # ------------------------------------------------------------------
    # Permissions and companies
    # ------------------------------------------------------------------
    def test_permissions(self):
        sale = self._sale(user=self.agent)
        sale.with_user(self.agent).action_book()
        # Agents cannot create invoices or read them, but see the invoicing status.
        with self.assertRaises(AccessError):
            sale.with_user(self.agent).action_create_booking_invoice()
        with self.assertRaises(AccessError):
            sale.with_user(self.agent).read(['invoice_ids'])
        self._invoice_fully(sale)
        self.assertEqual(sale.with_user(self.agent).invoice_status, 'invoiced')
        self.assertEqual(sale.with_user(self.agent).invoice_count, 2)
        # Another agent does not see this sale.
        self.assertNotIn(sale, self.env['property.sale.contract'].with_user(self.agent_2).search([]))
        # The accountant reads it but cannot change it.
        with self.assertRaises(AccessError):
            sale.with_user(self.accountant).write({'note': 'changed'})

    def test_company_boundaries(self):
        company_2 = self.setup_other_company()['company']
        type_2 = self.property_type
        owner_2 = self.env['res.partner'].create({'name': 'Owner 2', 'is_property_owner': True, 'company_id': company_2.id})
        villa_2 = self.env['property.property'].create({
            'name': 'Company 2 Villa', 'type_id': type_2.id, 'property_for': 'sale', 'owner_id': owner_2.id,
            'sale_price': 100000.0, 'company_id': company_2.id,
        })
        sale_2 = self.env['property.sale.contract'].with_company(company_2).create({
            'property_id': villa_2.id, 'buyer_id': self.buyer.id, 'booking_amount': 1000.0,
        })
        self.assertEqual(sale_2.company_id, company_2)
        sale_2.action_book()
        invoice = self.env['account.move'].browse(sale_2.with_company(company_2).action_create_booking_invoice()['res_id'])
        self.assertEqual(invoice.company_id, company_2)
        self.assertEqual(invoice.journal_id.company_id, company_2)
        # Users of the first company do not see it, and a sale cannot mix companies.
        self.assertNotIn(sale_2, self.env['property.sale.contract'].with_user(self.agent).search([]))
        with self.assertRaises(UserError):
            self._sale(property_id=villa_2.id)

    # ------------------------------------------------------------------
    # Documents, smart buttons and report
    # ------------------------------------------------------------------
    def test_documents_smart_buttons_and_report(self):
        sale = self._sale(user=self.agent)
        sale.action_book()
        invoices = self._invoice_fully(sale)
        self.env['ir.attachment'].create({
            'name': 'Agreement to sell.pdf', 'raw': b'%PDF-1.4 agreement',
            'res_model': 'property.sale.contract', 'res_id': sale.id,
        })
        self.assertEqual(sale.document_count, 1)
        self.assertEqual(self.env['ir.attachment'].search(sale.action_view_documents()['domain']).name, 'Agreement to sell.pdf')
        self.assertEqual(self.env['account.move'].search(sale.action_view_invoices()['domain']), invoices)

        html, _type = self.env['ir.actions.report'].with_user(self.agent)._render_qweb_html(
            'inom_rental_management.action_report_property_sale_contract', sale.ids,
        )
        html = html.decode()
        self.assertIn(sale.name, html)
        self.assertIn('Green Meadows Villa 12', html)
        for invoice in invoices:
            self.assertIn(invoice.name, html)
