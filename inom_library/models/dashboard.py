from odoo import api, fields, models


class InomPortalDashboard(models.AbstractModel):
    _inherit = 'inom.portal.dashboard'

    @api.model
    def _dash_library(self, scope):
        Loan = self.env['inom.loan']
        Copy = self.env['inom.book.copy']
        today = fields.Date.context_today(self)

        titles = self.env['inom.book'].search_count([])
        copies = Copy.search_count([])
        on_loan = Copy.search_count([('state', '=', 'issued')])
        overdue = Loan.search([('state', '=', 'issued'), ('due_on', '<', today)])
        fines_due = sum(overdue.mapped('fine_amount'))

        kpis = [
            self._kpi('Titles', titles),
            self._kpi('Copies', copies, hint='Physical copies, not titles.'),
            self._kpi('On loan', on_loan,
                      hint=f'{(on_loan / copies * 100) if copies else 0:.0f}% of the shelf.'),
            self._kpi('Overdue', len(overdue), tone='bad' if overdue else 'ok',
                      hint=f'Fines accrued: {fines_due:,.0f}'),
        ]

        cards = [
            {'cols': 2, 'items': [
                {'title': 'Catalogue by category', 'type': 'donut',
                 'values': [{'label': label, 'value': count} for label, count in
                            self._group_counts('inom.book', [], 'category')]},
                {'title': 'Copies by state', 'type': 'hbar',
                 'values': [{'label': label, 'value': count} for label, count in
                            self._group_counts('inom.book.copy', [], 'state')]},
            ]},
            {'cols': 1, 'items': [
                {'title': 'Overdue loans', 'sub': 'Oldest first',
                 'type': 'table',
                 'head': ['Student', 'Title', 'Due', 'Days over', 'Fine'],
                 'rows': [[l.student_id.name, l.book_id.title, str(l.due_on),
                           l.days_overdue, f'{l.fine_amount:,.0f}']
                          for l in overdue.sorted('due_on')[:12]]},
            ]},
        ]
        return {'kpis': kpis, 'cards': cards}
