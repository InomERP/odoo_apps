# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class InomEstimatePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'estimate_count' in counters:
            partner = request.env.user.partner_id
            try:
                count = request.env['inom.cost.estimate'].search_count([
                    ('partner_id', 'child_of', partner.commercial_partner_id.id),
                ])
            except AccessError:
                count = 0
            values['estimate_count'] = count
        return values

    @http.route(['/my/estimates', '/my/estimates/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_estimates(self, page=1, **kw):
        Estimate = request.env['inom.cost.estimate']
        partner = request.env.user.partner_id
        domain = [('partner_id', 'child_of', partner.commercial_partner_id.id)]
        total = Estimate.search_count(domain)
        pager = portal_pager(
            url='/my/estimates', total=total, page=page,
            step=self._items_per_page)
        estimates = Estimate.search(
            domain, limit=self._items_per_page,
            offset=pager['offset'], order='id desc')
        values = {
            'estimates': estimates,
            'page_name': 'estimate',
            'pager': pager,
            'default_url': '/my/estimates',
        }
        return request.render(
            'inom_job_cost_estimation.portal_my_estimates', values)

    @http.route(['/my/estimate/<int:estimate_id>'],
                type='http', auth='public', website=True)
    def portal_estimate_detail(self, estimate_id, access_token=None,
                               report_type=None, download=False, **kw):
        try:
            estimate_sudo = self._document_check_access(
                'inom.cost.estimate', estimate_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=estimate_sudo, report_type=report_type,
                report_ref='inom_job_cost_estimation.action_report_inom_estimate',
                download=download)
        values = {
            'estimate': estimate_sudo,
            'token': access_token,
            'page_name': 'estimate',
            'bootstrap_formatting': True,
        }
        return request.render(
            'inom_job_cost_estimation.portal_estimate_page', values)

    # A plain form POST. Odoo 19 has no reusable signature-pad template, so
    # acceptance is recorded as a typed name plus a timestamp.
    @http.route(['/my/estimate/<int:estimate_id>/accept'],
                type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def portal_estimate_accept(self, estimate_id, access_token=None, **post):
        try:
            estimate_sudo = self._document_check_access(
                'inom.cost.estimate', estimate_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        signer_name = post.get('signer_name')
        if signer_name:
            estimate_sudo._portal_sign(signer_name)
        return request.redirect(estimate_sudo.get_portal_url())
