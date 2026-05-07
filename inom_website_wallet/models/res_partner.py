# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    wallet_balance = fields.Monetary(
        string='Wallet Balance',
        compute='_compute_wallet_balance',
        store=True,
        currency_field='currency_id',
        help='Current available wallet balance for this customer.',
    )
    wallet_transaction_ids = fields.One2many(
        'website.wallet.transaction',
        'partner_id',
        string='Wallet Transactions',
    )
    wallet_transaction_count = fields.Integer(
        string='Wallet Transactions',
        compute='_compute_wallet_balance',
        store=True,
    )

    @api.depends(
        'wallet_transaction_ids',
        'wallet_transaction_ids.state',
        'wallet_transaction_ids.amount',
        'wallet_transaction_ids.transaction_type',
    )
    def _compute_wallet_balance(self):
        for partner in self:
            confirmed = partner.wallet_transaction_ids.filtered(
                lambda t: t.state == 'confirmed'
            )
            credits = sum(confirmed.filtered(
                lambda t: t.transaction_type == 'credit'
            ).mapped('amount'))
            debits = sum(confirmed.filtered(
                lambda t: t.transaction_type == 'debit'
            ).mapped('amount'))
            partner.wallet_balance = credits - debits
            partner.wallet_transaction_count = len(partner.wallet_transaction_ids)

    def action_open_wallet_transactions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'inom_website_wallet.action_website_wallet_transaction'
        )
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.id,
            'search_default_partner_id': self.id,
        }
        return action

    def action_add_wallet_balance(self):
        """Open the wizard to manually add money to the wallet."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Money to Wallet'),
            'res_model': 'add.wallet.balance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            },
        }
