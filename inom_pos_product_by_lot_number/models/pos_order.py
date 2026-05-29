# -*- coding: utf-8 -*-
from odoo import api, models


class PosOrder(models.Model):
    """
    Light extension to pos.order.

    The lot data itself lives at the order-line level (pack_lot_ids); this
    class only needs to ensure data-loading consistency and that stock is
    moved at the right time.
    """
    _inherit = 'pos.order'

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        fields_list = super()._load_pos_data_fields(*args, **kwargs)
        # Nothing extra to load at the header level.
        return fields_list

    # ─────────────────────────────────────────────────────────────────────
    # STOCK / LOT DECREMENT TIMING
    # ─────────────────────────────────────────────────────────────────────
    def _should_create_picking_real_time(self):
        """Force the delivery picking to be created (and validated) at PAYMENT
        time so that on-hand stock AND lot/serial quantities are decremented
        immediately, instead of only when the POS session is closed.

        WHY THIS FIXES THE ISSUE
        ------------------------
        In Odoo 17 core, ``pos.order._create_order_picking()`` only builds the
        stock picking when ``_should_create_picking_real_time()`` returns True.
        Core's default is::

            return not self.session_id.update_stock_at_closing or (
                self.company_id.anglo_saxon_accounting and self.to_invoice)

        If the POS config is set to update stock *at closing*
        (``update_stock_at_closing = True``) this returns False, so NO picking
        is created at payment — meaning the product's on-hand quantity and the
        selected lot/serial quantity are not reduced until the session is
        closed. That is exactly the "stock/lot not updating after payment"
        symptom.

        Returning True here makes core create the picking right away. Core then
        performs the real stock moves itself (``stock.picking.
        _create_picking_from_pos_order_lines`` maps each ``pack_lot_ids``
        lot_name to a ``stock.lot`` and reserves/consumes the matching quants).

        SAFETY (no duplicate moves / no double deduction)
        -------------------------------------------------
        ``_create_order_picking()`` begins with ``if self.picking_ids: return``,
        so once the picking exists it is never created again — neither the
        session-closing routine nor a second call can duplicate the moves. We
        do not create any stock.move / stock.quant ourselves; we only change
        the *timing* of core's single, existing code path. Refunds (negative
        qty) and invoicing keep working because we only widen the condition to
        always-real-time, which is a superset of core's own True cases.
        """
        # Preserve core's True cases, and additionally force real-time even
        # when the config would otherwise defer to session closing.
        return True
