from odoo import api, models


class InomPortalDashboard(models.AbstractModel):
    _inherit = 'inom.portal.dashboard'

    @api.model
    def _dash_overview(self, scope):
        data = super()._dash_overview(scope)
        pending = self.env['inom.certificate.request'].search_count(
            self._scope_domain(scope, model='inom.certificate.request')
            + [('state', '=', 'pending')])
        if pending:
            data['kpis'].append(self._kpi(
                'Certificates awaiting approval', pending, tone='warn'))
        return data

    @api.model
    def _dash_certs(self, scope):
        Request = self.env['inom.certificate.request']
        domain = self._scope_domain(scope, model='inom.certificate.request')

        pending = Request.search(domain + [('state', '=', 'pending')])
        approved = Request.search_count(domain + [('state', '=', 'approved')])
        issued = Request.search_count(domain + [('state', '=', 'issued')])
        rejected = Request.search_count(domain + [('state', '=', 'rejected')])

        kpis = [
            self._kpi('Awaiting approval', len(pending),
                      tone='warn' if pending else 'ok'),
            self._kpi('Approved, not yet issued', approved, tone='idle'),
            self._kpi('Issued', issued, tone='ok'),
            self._kpi('Rejected', rejected, tone='bad' if rejected else 'idle'),
        ]

        cards = [
            {'cols': 2, 'items': [
                {'title': 'Requests by type', 'type': 'hbar',
                 'values': [{'label': label, 'value': count} for label, count in
                            self._group_counts('inom.certificate.request',
                                               domain, 'type_id')]},
                {'title': 'Requests by stage', 'type': 'donut',
                 'values': [{'label': label, 'value': count} for label, count in
                            self._group_counts('inom.certificate.request',
                                               domain, 'state')]},
            ]},
            {'cols': 1, 'items': [
                {'title': 'Waiting on a decision', 'type': 'table',
                 'head': ['Reference', 'Student', 'Type', 'Requested'],
                 'rows': [[r.reference, r.student_id.name, r.type_id.name,
                           str(r.requested_on)]
                          for r in pending.sorted('requested_on')[:12]]},
            ]},
        ]
        return {'kpis': kpis, 'cards': cards}
