from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

# Leases started by the demo, with how many of their latest rent invoices are left unpaid.
DEMO_LEASES = {
    'inom_rental_management.demo_lease_skyline_a101': 0,
    'inom_rental_management.demo_lease_skyline_a102': 0,
    'inom_rental_management.demo_lease_skyline_b201': 2,
    'inom_rental_management.demo_lease_green_villa': 1,
    'inom_rental_management.demo_lease_metro_shop': 0,
}
DEMO_DEPOSITS = ('inom_rental_management.demo_lease_skyline_a101', 'inom_rental_management.demo_lease_metro_shop')


class PropertyRentalDemo(models.AbstractModel):
    """ Runs the demo records through their normal workflow, so that the demo database shows
    running leases, rent invoices, payments, overdue rent and property sales. Called from the
    demo data only. """
    _name = 'property.rental.demo'
    _description = 'Real Estate Demo Workflow'

    @api.model
    def _load_demo_workflow(self):
        admin = self.env.ref('base.user_admin')
        env = self.env(user=admin, su=False, context=dict(self.env.context, tracking_disable=True))
        company = admin.company_id
        env = env(context=dict(env.context, allowed_company_ids=company.ids))
        today = fields.Date.context_today(env['res.users'])

        leases = env['property.rental.contract']
        for xmlid in DEMO_LEASES:
            lease = env.ref(xmlid, raise_if_not_found=False)
            if lease and lease.state == 'draft':
                if company.rental_require_lease_approval:
                    lease.action_approve()
                lease.action_start()
                leases |= lease

        # Accounting needs a chart of accounts and a sales journal; without them the demo stops here.
        if not company.chart_template or not env['account.journal'].search_count(
                [('type', '=', 'sale'), ('company_id', '=', company.id)]):
            return

        for lease in leases:
            invoices = env['property.rent.schedule']._get_due_lines(lease)._create_invoices()
            invoices.filtered(lambda m: m.state == 'draft').action_post()
            unpaid = DEMO_LEASES[lease.get_external_id()[lease.id]]
            posted = lease.rental_move_ids.filtered(
                lambda m: m.state == 'posted' and m.property_rental_move_kind == 'rent'
            ).sorted('invoice_date')
            self._demo_pay(env, posted[:-unpaid] if unpaid else posted, today)

        for xmlid in DEMO_DEPOSITS:
            lease = env.ref(xmlid, raise_if_not_found=False)
            if lease in leases:
                lease.action_invoice_deposit()
                deposit = lease.rental_move_ids.filtered(lambda m: m.property_rental_move_kind == 'deposit')
                deposit.filtered(lambda m: m.state == 'draft').action_post()
                self._demo_pay(env, deposit, today)

        sold = env.ref('inom_rental_management.demo_sale_nh_plot', raise_if_not_found=False)
        if sold and sold.state == 'draft':
            sold.action_book()
            sold.action_create_booking_invoice()
            sold.action_create_balance_invoice()
            sold.invoice_ids.filtered(lambda m: m.state == 'draft').action_post()
            self._demo_pay(env, sold.invoice_ids, today)
            sold.action_sell()

        booked = env.ref('inom_rental_management.demo_sale_hill_top', raise_if_not_found=False)
        if booked and booked.state == 'draft':
            booked.action_book()
            booked.action_create_booking_invoice()
            booked.invoice_ids.filtered(lambda m: m.state == 'draft').action_post()
            self._demo_pay(env, booked.invoice_ids, today)

    @api.model
    def _demo_pay(self, env, invoices, today):
        for invoice in invoices.filtered(lambda m: m.state == 'posted' and m.payment_state == 'not_paid'):
            env['account.payment.register'].with_context(
                active_model='account.move', active_ids=invoice.ids,
            ).create({
                'payment_date': min(today, invoice.invoice_date + relativedelta(days=3)),
            }).action_create_payments()
