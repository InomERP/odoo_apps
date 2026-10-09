from odoo import api, fields, models


class InomPortalDashboard(models.AbstractModel):
    _inherit = 'inom.portal.dashboard'

    @api.model
    def _dash_overview(self, scope):
        data = super()._dash_overview(scope)
        # Only the roles that may see money get the money figure. Hiding it in
        # the browser would still have sent it over the wire.
        if not self.env.user._inom_permissions().get('money'):
            return data
        domain = self._scope_domain(scope, model='inom.fee.account')
        accounts = self.env['inom.fee.account'].search(domain)
        data['kpis'].append(self._kpi(
            'Fees outstanding',
            self._inr(sum(accounts.mapped('amount_due'))),
            tone='warn' if accounts.filtered(lambda a: a.state == 'overdue') else 'idle',
            hint='Across every open fee account in your scope.'))
        return data

    @api.model
    def _dash_finance(self, scope):
        Account = self.env['inom.fee.account']
        Line = self.env['inom.fee.account.line']
        domain = self._scope_domain(scope, model='inom.fee.account')
        today = fields.Date.context_today(self)

        accounts = Account.search(domain)
        billed = sum(accounts.mapped('amount_billed'))
        paid = sum(accounts.mapped('amount_paid'))
        due = sum(accounts.mapped('amount_due'))
        collection_rate = (paid / billed * 100.0) if billed else 0.0

        overdue_lines = Line.search([
            ('due_date', '<', today), ('amount_due', '>', 0),
        ] + self._scope_domain(scope, department_field='account_id.department_id',
                               model='inom.fee.account.line'))

        kpis = [
            self._kpi('Billed', self._inr(billed), hint='Total payable after scholarships.'),
            self._kpi('Collected', self._inr(paid), tone='ok'),
            self._kpi('Outstanding', self._inr(due), tone='warn' if due else 'ok'),
            self._kpi('Collection rate', f'{collection_rate:.1f}%',
                      tone='ok' if collection_rate >= 85 else 'warn',
                      hint='Collected as a share of what has been billed.'),
        ]

        by_state = self._group_counts('inom.fee.account', domain, 'state')
        by_department = self._read_sum('inom.fee.account', domain, 'department_id', 'amount_due')

        cards = [
            {'cols': 2, 'items': [
                {'title': 'Fee accounts by status', 'type': 'donut',
                 'values': [{'label': label, 'value': count} for label, count in by_state]},
                {'title': 'Outstanding by department', 'type': 'hbar',
                 'values': [{'label': label, 'value': round(total)}
                            for label, total in sorted(by_department, key=lambda r: -r[1])[:10]]},
            ]},
            {'cols': 1, 'items': [
                {'title': 'Overdue instalments',
                 'sub': f'{len(overdue_lines)} past their due date',
                 'type': 'table',
                 'head': ['Student', 'Instalment', 'Due', 'Amount'],
                 'rows': [[line.student_id.name, line.name,
                           fields.Date.to_string(line.due_date),
                           self._inr(line.amount_due)]
                          for line in overdue_lines[:12]]},
            ]},
        ]
        return {'kpis': kpis, 'cards': cards}

    # ------------------------------------------------------------------
    @api.model
    def _read_sum(self, model_name, domain, groupby, field):
        """[(label, total)] for one group-by and one summed field.

        Odoo 20: _read_group() takes field-spec strings and returns tuples, not
        dicts. Writing ``['amount_due:sum']`` and unpacking positionally is the
        correct shape; indexing the result like a dict is the Odoo 17 habit that
        fails silently here.
        """
        rows = self.env[model_name]._read_group(domain, [groupby], [f'{field}:sum'])
        out = []
        for value, total in rows:
            label = value.display_name if hasattr(value, 'display_name') else (
                'Not set' if value is False else str(value))
            out.append((label, total or 0.0))
        return out

    @api.model
    def _inr(self, amount):
        """Indian digit grouping, matching the prototype's number formatting."""
        amount = round(amount or 0)
        if amount >= 10000000:
            return f'₹{amount / 10000000:.2f} Cr'
        if amount >= 100000:
            return f'₹{amount / 100000:.2f} L'
        return f'₹{amount:,.0f}'
