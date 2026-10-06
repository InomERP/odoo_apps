# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    wallet_amount_used = fields.Monetary(
        string='Paid by Wallet',
        currency_field='currency_id',
        copy=False,
        help='Amount of this order paid using the customer wallet balance.',
        readonly=True,
    )
    wallet_transaction_ids = fields.One2many(
        'website.wallet.transaction',
        'sale_order_id',
        string='Wallet Transactions',
        copy=False,
        readonly=True,
    )
    wallet_transaction_count = fields.Integer(
        string='Wallet Transactions',
        compute='_compute_wallet_transaction_count',
    )
    is_wallet_recharge_order = fields.Boolean(
        string='Is Wallet Recharge Order',
        compute='_compute_is_wallet_recharge_order',
        store=True,
        help='True if this order contains the configured wallet recharge product.',
    )

    @api.depends('wallet_transaction_ids')
    def _compute_wallet_transaction_count(self):
        for order in self:
            order.wallet_transaction_count = len(order.wallet_transaction_ids)

    @api.depends('order_line.product_id')
    def _compute_is_wallet_recharge_order(self):
        recharge_product = self.env['res.config.settings'].sudo().get_wallet_recharge_product()
        for order in self:
            order.is_wallet_recharge_order = bool(
                recharge_product
                and order.order_line.filtered(
                    lambda l: l.product_id.id == recharge_product.id
                )
            )

    # ------------------------------------------------------------------
    # Confirm / cancel
    # ------------------------------------------------------------------
    def action_confirm(self):
        """Public confirmation entry point (manual confirm in backend)."""
        res = super().action_confirm()
        self._website_wallet_handle_recharge()
        return res

    def _action_confirm(self):
        """Internal confirmation entry point.

        This is the method invoked by Odoo's online-payment flow
        (``payment.transaction._post_process`` and friends), which is why
        we MUST hook here in addition to ``action_confirm`` -- otherwise
        wallet recharges paid online never trigger the credit transaction.
        """
        res = super()._action_confirm()
        self._website_wallet_handle_recharge()
        return res

    def _website_wallet_handle_recharge(self):
        """Idempotent dispatcher. Safe to call multiple times for the
        same order: ``_website_wallet_process_recharge_on_confirm`` skips
        orders that already have a credit transaction recorded."""
        for order in self:
            try:
                order._website_wallet_process_recharge_on_confirm()
            except Exception as e:  # noqa: BLE001
                # Never let wallet bookkeeping break the order-confirmation
                # / payment flow itself. Just log it so an admin can see.
                _logger.exception(
                    "Wallet recharge processing failed for order %s: %s",
                    order.display_name, e,
                )

    def _website_wallet_process_recharge_on_confirm(self):
        """When a sale order containing the wallet recharge product is
        confirmed, create the credit transaction so the customer's
        wallet balance is updated."""
        self.ensure_one()
        recharge_product = self.env['res.config.settings'].sudo().get_wallet_recharge_product()
        if not recharge_product:
            return
        recharge_lines = self.order_line.filtered(
            lambda l: l.product_id.id == recharge_product.id
        )
        if not recharge_lines:
            return
        # Skip if a credit transaction was already created for this order
        existing = self.wallet_transaction_ids.filtered(
            lambda t: t.transaction_type == 'credit' and t.state != 'cancelled'
        )
        if existing:
            return
        amount = sum(recharge_lines.mapped('price_subtotal'))
        if amount <= 0:
            return
        partner = self.partner_id.commercial_partner_id or self.partner_id
        transaction = self.env['website.wallet.transaction'].sudo().create({
            'partner_id': partner.id,
            'transaction_type': 'credit',
            'amount': amount,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'sale_order_id': self.id,
            'description': _('Wallet Recharge via Order %s', self.name),
        })
        transaction.action_confirm()

    # ------------------------------------------------------------------
    # Pay this order with the wallet
    # ------------------------------------------------------------------
    def action_pay_with_wallet(self):
        """Use the customer's wallet balance to pay (or partially pay) this
        order. Creates a debit transaction equal to the amount applied."""
        self.ensure_one()
        if self.state not in ('draft', 'sent', 'sale'):
            raise UserError(_("This order cannot be paid with the wallet in its current state."))
        partner = self.partner_id.commercial_partner_id or self.partner_id
        balance = partner.wallet_balance
        if balance <= 0:
            raise UserError(_("The customer has no wallet balance available."))
        # Don't pay more than what's left to pay on the order
        remaining = max(self.amount_total - self.wallet_amount_used, 0.0)
        amount_to_use = min(balance, remaining)
        if amount_to_use <= 0:
            raise UserError(_("Nothing left to pay with the wallet on this order."))
        transaction = self.env['website.wallet.transaction'].sudo().create({
            'partner_id': partner.id,
            'transaction_type': 'debit',
            'amount': amount_to_use,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'sale_order_id': self.id,
            'description': _('Used on Order %s', self.name or ''),
        })
        transaction.action_confirm()
        self.wallet_amount_used = (self.wallet_amount_used or 0.0) + amount_to_use
        return amount_to_use

    def action_view_wallet_transactions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'inom_website_wallet.action_website_wallet_transaction'
        )
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {'default_sale_order_id': self.id}
        return action
