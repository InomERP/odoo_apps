from datetime import datetime
from itertools import zip_longest

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.misc import formatLang

DASHBOARD_GROUPS = ('inom_rental_management.group_rental_manager', 'inom_rental_management.group_rental_accountant')
PERIODS = {
    'this_month': 'This Month',
    'last_month': 'Last Month',
    'last_30_days': 'Last 30 Days',
    'this_quarter': 'This Quarter',
    'this_year': 'This Year',
}
UPCOMING_DAYS = 30
CHART_RANGES = {
    'last_30_days': 'Last 30 Days',
    'last_6_months': 'Last 6 Months',
    'last_12_months': 'Last 12 Months',
}


class PropertyDashboard(models.AbstractModel):
    """ Headline figures of the Real Estate dashboard.

    Every figure is one aggregate query (search_count or _read_group) on the records it comes from:
    the cost does not grow with the number of properties, contracts or invoices. """
    _name = 'property.dashboard'
    _description = 'Real Estate Dashboard'

    @api.model
    def _period_dates(self, period):
        today = fields.Date.context_today(self)
        if period == 'last_month':
            start = today.replace(day=1) - relativedelta(months=1)
            return start, start + relativedelta(months=1, days=-1)
        if period == 'last_30_days':
            return today - relativedelta(days=29), today
        if period == 'this_quarter':
            start = today.replace(month=3 * ((today.month - 1) // 3) + 1, day=1)
            return start, start + relativedelta(months=3, days=-1)
        if period == 'this_year':
            return today.replace(month=1, day=1), today.replace(month=12, day=31)
        start = today.replace(day=1)
        return start, start + relativedelta(months=1, days=-1)

    @api.model
    def _check_dashboard_access(self):
        if not any(self.env.user.has_group(group) for group in DASHBOARD_GROUPS):
            raise AccessError(self.env._("Only Property Managers and Real Estate Accountants can open the dashboard."))

    @api.model
    def _action(self, name, model, domain, views=('list', 'form'), context=None):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'domain': domain,
            'views': [[False, view] for view in views],
            'context': context or {},
            'target': 'current',
        }

    @api.model
    def get_dashboard_data(self, period='this_month', chart_range='last_6_months'):
        self._check_dashboard_access()
        if period not in PERIODS:
            period = 'this_month'
        if chart_range not in CHART_RANGES:
            chart_range = 'last_6_months'
        date_from, date_to = self._period_dates(period)
        today = fields.Date.context_today(self)
        companies = self.env.companies
        company_domain = [('company_id', 'in', companies.ids)]
        currency = self.env.company.currency_id
        money = lambda amount: formatLang(self.env, amount, currency_obj=currency)
        env = self.env(su=True)  # aggregates only; the visible figures are restricted to the allowed companies

        # Properties: one grouped query.
        Property = env['property.property']
        property_counts = {
            (state, purpose): count
            for state, purpose, count in Property._read_group(
                company_domain, ['state', 'property_for'], ['__count'],
            )
        }
        count = lambda states=None, purpose=None: sum(
            c for (s, p), c in property_counts.items()
            if (states is None or s in states) and (purpose is None or p == purpose)
        )
        [[total_before]] = Property._read_group(company_domain + [('create_date', '<', date_from)], [], ['__count'])
        rent_properties = count(purpose='rent')
        occupied = count(states=('rented',), purpose='rent')
        vacant = count(states=('draft', 'available'), purpose='rent')

        # Leases.
        Contract = env['property.rental.contract']
        expiring_limit = today + relativedelta(days=UPCOMING_DAYS)
        active_contracts = Contract.search_count(company_domain + [('state', '=', 'running')])
        expiring_domain = company_domain + [
            ('state', '=', 'running'), ('date_end', '>=', today), ('date_end', '<=', expiring_limit),
        ]
        expiring = Contract.search_count(expiring_domain)

        # Rent due in the next days, from the billing schedule.
        due_domain = company_domain + [
            ('date_due', '>=', today), ('date_due', '<=', expiring_limit),
            ('state', 'in', ('pending', 'draft', 'invoiced')),
        ]
        [[upcoming_due]] = env['property.rent.schedule']._read_group(due_domain, [], ['amount:sum'])

        # Overdue rent, from posted invoices.
        overdue_domain = company_domain + [
            ('property_rental_move_kind', '=', 'rent'), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')), ('invoice_date_due', '<', today),
        ]
        [[overdue_amount, overdue_count]] = env['account.move']._read_group(
            overdue_domain, [], ['amount_residual_signed:sum', '__count'],
        )

        # Rental income of the period: invoiced (by invoice date) and collected (by payment date).
        invoiced_domain = company_domain + [
            ('property_rental_move_kind', '=', 'rent'), ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from), ('invoice_date', '<=', date_to),
        ]
        [[invoiced]] = env['account.move']._read_group(invoiced_domain, [], ['amount_untaxed_signed:sum'])
        collected = self._rent_collected(env, companies, date_from, date_to)

        # Property sales of the period.
        Sale = env['property.sale.contract']
        sold_domain = company_domain + [('state', '=', 'sold'), ('date_sold', '>=', date_from), ('date_sold', '<=', date_to)]
        [[sold_count, sold_value]] = Sale._read_group(sold_domain, [], ['__count', 'sale_price:sum'])
        booked_domain = company_domain + [('state', '=', 'booked')]
        [[booked_count, booked_value]] = Sale._read_group(booked_domain, [], ['__count', 'sale_price:sum'])

        P, R, S = 'property.property', 'property.rental.contract', 'property.sale.contract'
        tiles = {
            'properties': [
                self._tile('total', "Total Properties", count(), self._action("Properties", P, company_domain)),
                self._tile('available', "Available", count(states=('available',)),
                           self._action("Available Properties", P, company_domain + [('state', '=', 'available')])),
                self._tile('for_sale', "For Sale", count(purpose='sale'),
                           self._action("Properties for Sale", P, company_domain + [('property_for', '=', 'sale')])),
                self._tile('for_rent', "For Rent", rent_properties,
                           self._action("Properties for Rent", P, company_domain + [('property_for', '=', 'rent')])),
                self._tile('occupied', "Occupied", occupied,
                           self._action("Occupied Properties", P, company_domain + [('property_for', '=', 'rent'), ('state', '=', 'rented')]),
                           hint=self.env._("%(rate)s%% of rental properties", rate=round(100 * occupied / rent_properties) if rent_properties else 0)),
                self._tile('vacant', "Vacant", vacant,
                           self._action("Vacant Properties", P, company_domain + [('property_for', '=', 'rent'), ('state', 'in', ('draft', 'available'))])),
            ],
            'leases': [
                self._tile('active_contracts', "Active Rental Contracts", active_contracts,
                           self._action("Active Rental Contracts", R, company_domain + [('state', '=', 'running')])),
                self._tile('expiring', "Expiring in 30 Days", expiring,
                           self._action("Expiring Rental Contracts", R, expiring_domain)),
                self._tile('upcoming_due', "Rent Due in 30 Days", money(upcoming_due),
                           self._action("Upcoming Rent", 'property.rent.schedule', due_domain), raw=upcoming_due),
            ],
            'finance': [],
            'sales': [
                self._tile('sold', "Sold in Period", sold_count,
                           self._action("Sold Properties", S, sold_domain), hint=money(sold_value), raw_value=sold_value),
                self._tile('booked', "Booked, Not Yet Sold", booked_count,
                           self._action("Booked Sales", S, booked_domain), hint=money(booked_value), raw_value=booked_value),
            ],
        }
        if self.env.user.has_group('account.group_account_invoice'):
            moves = lambda name, domain: self._action(name, 'account.move', domain, context={'create': False})
        else:
            moves = lambda name, domain: False  # figures shown, invoices not openable without Invoicing access
        tiles['finance'] = [
            self._tile('rent_invoiced', "Rent Invoiced", money(invoiced), moves("Rent Invoiced", invoiced_domain),
                       raw=invoiced, hint=self.env._("untaxed, by invoice date")),
            self._tile('rent_collected', "Rent Collected", money(collected), False,
                       raw=collected, hint=self.env._("payments received, by payment date")),
            self._tile('overdue', "Overdue Rent", money(overdue_amount), moves("Overdue Rent", overdue_domain),
                       raw=overdue_amount, hint=self.env._("%(count)s invoices", count=overdue_count)),
        ]
        return {
            'period': period,
            'periods': [[key, self.env._(label)] for key, label in PERIODS.items()],
            'summary': {
                'total': count(),
                'total_before_period': total_before,
                'occupancy_rate': round(100 * occupied / rent_properties) if rent_properties else 0,
                'collection_rate': round(100 * collected / invoiced) if invoiced else 0,
                'overdue_count': overdue_count,
            },
            'charts': {
                'status': self._status_chart(property_counts),
                'income': self._income_chart(env, companies, today, money, chart_range),
            },
            'lists': {
                'expiring': self._expiring_list(Contract, expiring_domain, today),
                'overdue_tenants': self._overdue_tenants(env, overdue_domain, money),
                'activity': self._recent_activity(env, companies, money),
            },
            'calendar': self._calendar_events(env, companies, today),
            'quick_actions': self._quick_actions(),
            'can_open_invoices': self.env.user.has_group('account.group_account_invoice'),
            'chart_range': chart_range,
            'chart_ranges': [[key, self.env._(label)] for key, label in CHART_RANGES.items()],
            'date_from': fields.Date.to_string(date_from),
            'date_to': fields.Date.to_string(date_to),
            'companies': companies.mapped('name'),
            'currency': currency.name,
            'tiles': tiles,
        }

    @api.model
    def _status_chart(self, property_counts):
        labels = dict(self.env['property.property']._fields['state']._description_selection(self.env))
        totals = {}
        for (state, _purpose), number in property_counts.items():
            totals[state] = totals.get(state, 0) + number
        return [
            {'key': state, 'label': labels[state], 'value': totals.get(state, 0)}
            for state in ('available', 'rented', 'booked', 'sold', 'draft')
        ]

    @api.model
    def _income_chart(self, env, companies, today, money, chart_range='last_6_months'):
        """ Rent invoiced and collected per day (last 30 days) or per month: two grouped queries. """
        if chart_range == 'last_30_days':
            first, last, granularity, step = today - relativedelta(days=29), today, 'day', relativedelta(days=1)
            buckets = 30
        else:
            buckets = 12 if chart_range == 'last_12_months' else 6
            first = today.replace(day=1) - relativedelta(months=buckets - 1)
            last = today.replace(day=1) + relativedelta(months=1, days=-1)
            granularity, step = 'month', relativedelta(months=1)
        invoiced = dict(env['account.move']._read_group([
            ('company_id', 'in', companies.ids), ('property_rental_move_kind', '=', 'rent'), ('state', '=', 'posted'),
            ('invoice_date', '>=', first), ('invoice_date', '<=', last),
        ], [f'invoice_date:{granularity}'], ['amount_untaxed_signed:sum']))
        collected = dict(env['account.partial.reconcile']._read_group([
            ('company_id', 'in', companies.ids), ('max_date', '>=', first), ('max_date', '<=', last),
            ('debit_move_id.move_id.property_rental_move_kind', '=', 'rent'),
            ('debit_move_id.move_id.move_type', '=', 'out_invoice'),
            ('credit_move_id.move_id.move_type', '=', 'entry'),
        ], [f'max_date:{granularity}'], ['amount:sum']))
        points = []
        for offset in range(buckets):
            bucket = first + step * offset
            daily = granularity == 'day'
            points.append({
                'label': bucket.strftime('%d %B %Y' if daily else '%B %Y'),
                'short_label': f"{bucket.strftime('%b')} {bucket.day}" if daily else bucket.strftime('%b'),
                'invoiced': invoiced.get(bucket, 0.0),
                'collected': collected.get(bucket, 0.0),
                'invoiced_display': money(invoiced.get(bucket, 0.0)),
                'collected_display': money(collected.get(bucket, 0.0)),
            })
        return points

    @api.model
    def _calendar_events(self, env, companies, today, limit=4):
        """ Upcoming dates of the next 30 days, one entry per day and kind: grouped queries only. """
        company_domain = [('company_id', 'in', companies.ids)]
        until = today + relativedelta(days=UPCOMING_DAYS)
        events = []
        for day, number in env['property.rent.schedule']._read_group(company_domain + [
            ('date_due', '>=', today), ('date_due', '<=', until), ('state', 'in', ('pending', 'draft', 'invoiced')),
            ('contract_id.state', 'in', ('running', 'approved')),
        ], ['date_due:day'], ['contract_id:count_distinct']):
            events.append(self._calendar_event(
                day, 'rent', self.env._("Rent Due"), number, self.env._("Pending"), 'warning',
                self._action(self.env._("Rent Due"), 'property.rent.schedule', company_domain + [
                    ('date_due', '=', day), ('state', 'in', ('pending', 'draft', 'invoiced'))])))
        for day, number in env['property.rental.contract']._read_group(company_domain + [
            ('state', '=', 'running'), ('date_end', '>=', today), ('date_end', '<=', until),
        ], ['date_end:day'], ['__count']):
            events.append(self._calendar_event(
                day, 'lease', self.env._("Lease Expiry"), number, self.env._("Upcoming"), 'orange',
                self._action(self.env._("Expiring Leases"), 'property.rental.contract', company_domain + [
                    ('state', '=', 'running'), ('date_end', '=', day)])))
        events += self._calendar_extra_events(env, companies, today, until)
        events.sort(key=lambda event: (event['date'], event['kind']))
        return events[:limit]

    @api.model
    def _calendar_extra_events(self, env, companies, today, until):
        """ Hook for other modules to add their dates to the dashboard calendar. """
        return []

    @api.model
    def _calendar_event(self, day, kind, title, number, badge, tone, action):
        if isinstance(day, datetime):
            day = day.date()
        return {
            'id': f'{kind}-{day}',
            'kind': kind,
            'date': fields.Date.to_string(day),
            'day': day.day,
            'month': day.strftime('%b'),
            'title': title,
            'detail': self.env._("%(count)s properties", count=number) if number != 1 else self.env._("1 property"),
            'badge': badge,
            'tone': tone,
            'action': action,
        }

    @api.model
    def _quick_actions(self):
        """ Shortcuts shown only to users allowed to use them. """
        form = lambda model: {'type': 'ir.actions.act_window', 'res_model': model, 'views': [[False, 'form']],
                              'target': 'current'}
        actions = []
        if self.env['property.property'].has_access('create'):
            actions.append({'key': 'property', 'label': self.env._("Add Property"), 'action': form('property.property')})
        if self.env['property.rental.contract'].has_access('create'):
            actions.append({'key': 'lease', 'label': self.env._("New Lease"), 'action': form('property.rental.contract')})
        if self.env.user.has_group('account.group_account_invoice'):
            actions.append({'key': 'payment', 'label': self.env._("Record Payment"),
                            'action': 'inom_rental_management.action_outstanding_rent'})
        actions.append({'key': 'report', 'label': self.env._("Generate Report"),
                        'action': 'inom_rental_management.action_report_rental_income_property'})
        return actions

    @api.model
    def _names(self, env, model, ids):
        """ Display names of records in one query, whatever is already cached, so that the query
        count does not depend on the data. """
        records = env[model].with_context(active_test=False).search_fetch([('id', 'in', list(set(ids)))], ['name'])
        return {record.id: record.name for record in records}

    @api.model
    def _expiring_list(self, Contract, expiring_domain, today):
        contracts = Contract.search_fetch(expiring_domain, ['name', 'date_end', 'property_id', 'tenant_id'],
                                          order='date_end asc, id asc', limit=5)
        properties = self._names(Contract.env, 'property.property', contracts.property_id._ids)
        tenants = self._names(Contract.env, 'res.partner', contracts.tenant_id._ids)
        return [{
            'id': contract.id,
            'name': contract.name,
            'property': properties.get(contract.property_id.id, ''),
            'tenant': tenants.get(contract.tenant_id.id, ''),
            'date_end': fields.Date.to_string(contract.date_end),
            'days': (contract.date_end - today).days,
            'action': {'type': 'ir.actions.act_window', 'res_model': 'property.rental.contract',
                       'res_id': contract.id, 'views': [[False, 'form']], 'target': 'current'},
        } for contract in contracts]

    @api.model
    def _overdue_tenants(self, env, overdue_domain, money):
        groups = env['account.move']._read_group(
            overdue_domain, ['partner_id'], ['amount_residual_signed:sum', '__count'],
            order='amount_residual_signed:sum desc', limit=5,
        )
        can_open = self.env.user.has_group('account.group_account_invoice')
        return [{
            'id': partner.id,
            'name': partner.name,
            'amount': amount,
            'amount_display': money(amount),
            'count': number,
            'action': self._action(
                self.env._("Overdue Rent: %(tenant)s", tenant=partner.name), 'account.move',
                overdue_domain + [('partner_id', '=', partner.id)], context={'create': False},
            ) if can_open else False,
        } for partner, amount, number in groups]

    @api.model
    def _recent_activity(self, env, companies, money, limit=6):
        """ Latest events across properties, leases, rent payments and sales: a fixed number of queries. """
        company_domain = [('company_id', 'in', companies.ids)]
        record_action = lambda model, res_id: {'type': 'ir.actions.act_window', 'res_model': model, 'res_id': res_id,
                                               'views': [[False, 'form']], 'target': 'current'}
        lease_states = dict(env['property.rental.contract']._fields['state']._description_selection(self.env))
        newest = lambda date: f'{date} desc, id desc'
        props = env['property.property'].search_fetch(company_domain, ['name', 'create_date'],
                                                       order=newest('create_date'), limit=limit)
        leases = env['property.rental.contract'].search_fetch(company_domain, ['name', 'state', 'write_date', 'property_id'],
                                                              order=newest('write_date'), limit=limit)
        sales = env['property.sale.contract'].search_fetch(company_domain + [('state', '=', 'sold')],
                                                           ['write_date', 'property_id', 'sale_price'],
                                                           order=newest('write_date'), limit=limit)
        partials = env['account.partial.reconcile'].search_fetch(company_domain + [
            ('debit_move_id.move_id.property_rental_move_kind', '=', 'rent'),
            ('debit_move_id.move_id.move_type', '=', 'out_invoice'),
            ('credit_move_id.move_id.move_type', '=', 'entry'),
        ], ['amount', 'create_date', 'debit_move_id'], order=newest('create_date'), limit=limit)
        lines = env['account.move.line'].search_fetch([('id', 'in', partials.debit_move_id.ids)], ['move_id', 'partner_id'])
        property_names = self._names(env, 'property.property', leases.property_id._ids + sales.property_id._ids)
        partner_names = self._names(env, 'res.partner', lines.partner_id._ids)
        can_open = self.env.user.has_group('account.group_account_invoice')

        props_events = [{
            'kind': 'property', 'title': self.env._("Property Added"), 'detail': prop.name,
            'when': prop.create_date, 'action': record_action('property.property', prop.id),
        } for prop in props]
        lease_events = [{
            'kind': 'lease', 'title': self.env._("Lease %(state)s", state=lease_states[lease.state]),
            'detail': f"{lease.name} · {property_names.get(lease.property_id.id, '')}", 'when': lease.write_date,
            'action': record_action('property.rental.contract', lease.id),
        } for lease in leases]
        payment_events = [{
            'kind': 'payment', 'title': self.env._("Rent Received"),
            'detail': f"{money(partial.amount)} · {partner_names.get(partial.debit_move_id.partner_id.id, '')}",
            'when': partial.create_date,
            'action': record_action('account.move', partial.debit_move_id.move_id.id) if can_open else False,
        } for partial in partials]
        sale_events = [{
            'kind': 'sale', 'title': self.env._("Property Sold"),
            'detail': f"{property_names.get(sale.property_id.id, '')} · {money(sale.sale_price)}", 'when': sale.write_date,
            'action': record_action('property.sale.contract', sale.id),
        } for sale in sales]
        # Interleave the kinds first, so that events recorded at the same moment show a mix.
        events = [event for group in zip_longest(props_events, lease_events, payment_events, sale_events)
                  for event in group if event]
        events.sort(key=lambda event: event['when'], reverse=True)
        events = events[:limit]
        for index, event in enumerate(events):
            event['id'] = index
            event['when'] = fields.Datetime.to_string(event['when'])
        return events

    @api.model
    def _tile(self, key, label, value, action, hint=False, raw=None, raw_value=None):
        return {
            'key': key,
            'label': self.env._(label),
            'value': value,
            'raw': raw if raw is not None else value,
            'raw_value': raw_value,
            'hint': hint,
            'action': action,
        }

    @api.model
    def _rent_collected(self, env, companies, date_from, date_to):
        """ Amounts matched on rent invoices by payments or bank lines (journal entries, not credit
        notes), dated within the period. """
        [[amount]] = env['account.partial.reconcile']._read_group([
            ('company_id', 'in', companies.ids),
            ('max_date', '>=', date_from), ('max_date', '<=', date_to),
            ('debit_move_id.move_id.property_rental_move_kind', '=', 'rent'),
            ('debit_move_id.move_id.move_type', '=', 'out_invoice'),
            ('credit_move_id.move_id.move_type', '=', 'entry'),
        ], [], ['amount:sum'])
        return amount


class PropertyNotification(models.AbstractModel):
    """ Daily internal reminders, as To-Do activities for the person responsible.

    Each reminder is created once: a flag on the record (or an existing activity) prevents
    the next run from creating it again. """
    _name = 'property.notification'
    _description = 'Real Estate Notifications'

    @api.model
    def _cron_send_notifications(self):
        self._notify_rent_due()
        self._notify_overdue_rent()
        self._notify_pending_enquiries()

    @api.model
    def _todo(self, record, user, summary, note='', deadline=None):
        if not user or not user.active or user.share:
            return False
        record.activity_schedule(
            'mail.mail_activity_data_todo',
            date_deadline=deadline or fields.Date.context_today(self),
            summary=summary, note=note, user_id=user.id,
        )
        return True

    @api.model
    def _notify_rent_due(self):
        today = fields.Date.context_today(self)
        Schedule = self.env['property.rent.schedule'].sudo()
        for company in self.env['res.company'].sudo().search([]):
            days = company.rental_rent_due_notice_days
            if days <= 0:
                continue
            lines = Schedule.search([
                ('company_id', '=', company.id),
                ('due_reminder_sent', '=', False),
                ('state', 'in', ('pending', 'draft', 'invoiced')),
                ('date_due', '>=', today), ('date_due', '<=', today + relativedelta(days=days)),
                ('contract_id.state', 'in', ('running', 'expired')),
            ])
            for line in lines:
                contract = line.contract_id
                self._todo(
                    contract, contract.user_id,
                    self.env._("Rent due on %(date)s: %(amount)s", date=line.date_due,
                               amount=formatLang(self.env, line.amount, currency_obj=line.currency_id)),
                    deadline=line.date_due,
                )
            lines.due_reminder_sent = True

    @api.model
    def _notify_overdue_rent(self):
        today = fields.Date.context_today(self)
        invoices = self.env['account.move'].sudo().search([
            ('property_rental_move_kind', '=', 'rent'), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')), ('invoice_date_due', '<', today),
            ('rental_overdue_notified', '=', False), ('property_rental_contract_id', '!=', False),
        ])
        for invoice in invoices:
            contract = invoice.property_rental_contract_id
            self._todo(
                contract, contract.user_id,
                self.env._("Overdue rent: %(invoice)s, %(amount)s due since %(date)s", invoice=invoice.name,
                           amount=formatLang(self.env, invoice.amount_residual, currency_obj=invoice.currency_id),
                           date=invoice.invoice_date_due),
                note=self.env._("Follow up with the tenant %(tenant)s.", tenant=invoice.partner_id.display_name),
            )
        invoices.rental_overdue_notified = True

    @api.model
    def _notify_pending_enquiries(self):
        now = fields.Datetime.now()
        Lead = self.env['crm.lead'].sudo()
        for company in self.env['res.company'].sudo().search([]):
            days = company.rental_enquiry_pending_days
            if days <= 0:
                continue
            leads = Lead.search([
                ('company_id', 'in', (company.id, False)),
                ('property_for', '!=', False), ('won_status', '=', 'pending'),
                ('property_enquiry_state', '=', 'open'),
                ('activity_ids', '=', False),
                ('write_date', '<=', now - relativedelta(days=days)),
            ])
            for lead in leads:
                self._todo(lead, lead.user_id, self.env._("Pending enquiry: no follow-up planned"))
