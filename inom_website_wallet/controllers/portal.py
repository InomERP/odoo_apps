# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CustomerPortalWallet(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id.commercial_partner_id
        if partner:
            if 'wallet_count' in counters:
                values['wallet_count'] = request.env[
                    'website.wallet.transaction'
                ].sudo().search_count([('partner_id', '=', partner.id)])
            values['wallet_balance'] = partner.wallet_balance
        else:
            values.setdefault('wallet_count', 0)
            values.setdefault('wallet_balance', 0.0)
        return values

    @http.route(
        ['/my/wallet/transactions',
         '/my/wallet/transactions/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_wallet_transactions(self, page=1, sortby=None, **kw):
        partner = request.env.user.partner_id.commercial_partner_id
        Tx = request.env['website.wallet.transaction'].sudo()
        domain = [('partner_id', '=', partner.id)]
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'date desc, id desc'},
            'amount': {'label': _('Amount'), 'order': 'amount desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        tx_count = Tx.search_count(domain)
        pager = portal_pager(
            url='/my/wallet/transactions',
            url_args={'sortby': sortby},
            total=tx_count,
            page=page,
            step=20,
        )
        transactions = Tx.search(
            domain, order=order, limit=20, offset=pager['offset']
        )
        values = {
            'transactions': transactions,
            'page_name': 'wallet',
            'pager': pager,
            'default_url': '/my/wallet/transactions',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'partner': partner,
            'wallet_balance': partner.wallet_balance,
            'currency': partner.currency_id or request.env.company.currency_id,
        }
        return request.render(
            'inom_website_wallet.portal_my_wallet_transactions', values,
        )

    @http.route(['/my/wallet/transaction/<int:transaction_id>'],
                type='http', auth='user', website=True)
    def portal_wallet_transaction_detail(self, transaction_id, **kw):
        try:
            tx = self._document_check_access(
                'website.wallet.transaction', transaction_id
            )
        except (AccessError, MissingError):
            return request.redirect('/my')
        return request.render(
            'inom_website_wallet.portal_wallet_transaction_detail',
            {'transaction': tx, 'page_name': 'wallet'},
        )

    def _document_check_access(self, model_name, document_id, access_token=None):
        # Allow customers to access their own wallet transactions.
        if model_name == 'website.wallet.transaction':
            partner = request.env.user.partner_id.commercial_partner_id
            tx = request.env[model_name].sudo().browse(document_id).exists()
            if not tx or tx.partner_id != partner:
                raise AccessError(_("You do not have access to this transaction."))
            return tx
        return super()._document_check_access(model_name, document_id, access_token)
