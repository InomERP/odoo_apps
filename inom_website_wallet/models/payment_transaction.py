# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    """Trigger the wallet credit transaction as soon as a payment is
    marked done OR pending.

    Background
    ----------
    The wallet credit was originally only created when the related
    ``sale.order`` was confirmed (state -> 'sale'). That works on
    payment providers that auto-confirm the order, but for offline
    methods (Wire Transfer / Manual) the order stays in 'sent' state
    until a salesperson manually verifies the payment, so the credit
    never appears in the customer's portal.

    Hooking ``payment.transaction._set_done`` and ``_set_pending`` lets
    us detect "payment received / promised" independently of the order
    state. The dispatcher we call (``_website_wallet_handle_recharge``)
    is idempotent: it skips orders that already have a credit
    transaction, so this is safe to combine with the existing
    ``sale.order.action_confirm`` / ``_action_confirm`` overrides.
    """
    _inherit = 'payment.transaction'

    def _set_done(self, **kwargs):
        res = super()._set_done(**kwargs)
        self._website_wallet_credit_recharge_orders()
        return res

    def _set_pending(self, **kwargs):
        res = super()._set_pending(**kwargs)
        self._website_wallet_credit_recharge_orders()
        return res

    def _set_authorized(self, **kwargs):
        # Some providers go via 'authorized' on capture-on-confirm flows.
        res = super()._set_authorized(**kwargs)
        self._website_wallet_credit_recharge_orders()
        return res

    def _website_wallet_credit_recharge_orders(self):
        """Fire the recharge credit on every linked sale order."""
        for tx in self:
            orders = tx.sale_order_ids if hasattr(tx, 'sale_order_ids') else False
            if not orders:
                continue
            try:
                # _website_wallet_handle_recharge is the same idempotent
                # dispatcher used by sale.order.action_confirm; safe to
                # call here regardless of the order's confirmation state.
                orders.sudo()._website_wallet_handle_recharge()
            except Exception as e:  # noqa: BLE001
                _logger.exception(
                    "Wallet recharge handling from payment.transaction "
                    "%s failed: %s", tx.reference, e,
                )
