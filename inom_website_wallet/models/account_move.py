# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    wallet_amount_used = fields.Monetary(
        string='Paid by Wallet',
        currency_field='currency_id',
        copy=False,
        readonly=True,
    )
    wallet_transaction_ids = fields.One2many(
        'website.wallet.transaction',
        'account_move_id',
        string='Wallet Transactions',
        copy=False,
        readonly=True,
    )
    has_wallet_balance = fields.Boolean(
        string='Customer has Wallet Balance',
        compute='_compute_has_wallet_balance',
    )

    @api.depends('partner_id', 'partner_id.commercial_partner_id.wallet_balance', 'state', 'move_type')
    def _compute_has_wallet_balance(self):
        for move in self:
            move.has_wallet_balance = (
                move.move_type in ('out_invoice', 'out_refund')
                and move.partner_id
                and move.partner_id.commercial_partner_id.wallet_balance > 0
            )

    def action_apply_wallet_balance(self):
        """Apply (a portion of) the customer's wallet balance as a payment
        against this customer invoice."""
        self.ensure_one()
        if self.move_type != 'out_invoice':
            raise UserError(_("Wallet balance can only be applied to customer invoices."))
        if self.state != 'posted':
            raise UserError(_("Please post the invoice before applying the wallet balance."))
        if self.payment_state in ('paid', 'in_payment', 'reversed'):
            raise UserError(_("This invoice is already paid."))
        partner = self.partner_id.commercial_partner_id or self.partner_id
        balance = partner.wallet_balance
        if balance <= 0:
            raise UserError(_("The customer has no available wallet balance."))
        amount_residual = self.amount_residual
        if amount_residual <= 0:
            raise UserError(_("Nothing left to pay on this invoice."))
        amount_to_use = min(balance, amount_residual)
        transaction = self.env['website.wallet.transaction'].sudo().create({
            'partner_id': partner.id,
            'transaction_type': 'debit',
            'amount': amount_to_use,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'account_move_id': self.id,
            'description': _('Used on Invoice %s', self.name or ''),
        })
        transaction.action_confirm()
        self.wallet_amount_used = (self.wallet_amount_used or 0.0) + amount_to_use

        # Try to register the payment via account.payment.register so
        # the invoice payment_state is updated.
        try:
            wallet_journal = transaction._get_wallet_journal()
            payment_register = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=self.ids,
            ).create({
                'amount': amount_to_use,
                'payment_date': fields.Date.context_today(self),
                'journal_id': wallet_journal.id,
                'communication': _('Wallet Payment - %s', transaction.name),
            })
            payment_register.action_create_payments()
        except Exception:
            # If accounting setup is incomplete just leave the transaction
            # recorded; the wallet balance is still updated.
            pass
        return True

    def action_view_wallet_transactions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'inom_website_wallet.action_website_wallet_transaction'
        )
        action['domain'] = [('account_move_id', '=', self.id)]
        action['context'] = {'default_account_move_id': self.id}
        return action
