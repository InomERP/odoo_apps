# -*- coding: utf-8 -*-
"""
Custom JSON controllers for the POS Lot/Serial module.

The bulk of POS<->backend traffic flows through the standard ORM RPC
(/web/dataset/call_kw). These custom endpoints are for:
  * The connectivity ping used by the offline detector (Phase 5)
  * Batch offline-sync of queued lot creates (Phase 5)
"""
from odoo import http
from odoo.http import request


class PosLotController(http.Controller):

    @http.route(
        '/inom_pos_lot/ping',
        type='json', auth='user', methods=['POST'], csrf=False,
    )
    def ping(self):
        """Health-check used by the frontend's offline detector."""
        return {
            'status': 'ok',
            'version': '19.0.1.5.0',
            'user_id': request.env.user.id,
            'company_id': request.env.company.id,
        }

    @http.route(
        '/inom_pos_lot/sync_offline_creates',
        type='json', auth='user', methods=['POST'], csrf=False,
    )
    def sync_offline_creates(self, batch=None):
        """
        Drain the offline lot-create queue.
        Delegates to stock.lot.sync_offline_lot_creates so the same
        validation/auth/idempotency logic applies whether the client
        calls call_kw directly or this convenience endpoint.
        """
        return request.env['stock.lot'].sudo(False).sync_offline_lot_creates(
            batch or []
        )
