# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    """
    pos.session extension.

    ROOT-CAUSE NOTE (Odoo 19):
    -------------------------
    The POS startup crash:

        TypeError: Cannot read properties of undefined (reading 'currency_id')
            at PosStore.processServerData (pos_store.js)

    is caused when the POS relational data graph is malformed during load.
    In Odoo 19, `processServerData()` does:

        this.config   = this.data.models["pos.config"].getFirst();
        this.currency = this.config.currency_id;   // <-- crash if config is undefined

    If anything corrupts the model graph that the loader walks, `pos.config`
    fails to resolve, `getFirst()` returns `undefined`, and reading
    `currency_id` throws.

    This module previously corrupted that graph by overriding
    `_load_pos_data_models` to force-inject `stock.lot` and
    `pos.pack.operation.lot` into the preload. We DELIBERATELY do NOT do
    that here.

    How lot data reaches the frontend instead:
      * Lots are fetched on demand via the stock.lot RPC methods
        (get_lots_by_product / search_lots_autocomplete / get_lot_by_name),
        which the popup calls in _refreshFromBackend().
      * `pos.pack.operation.lot` is already loaded by core POS with the
        correct, curated field list — no override needed.
      * The offline IndexedDB cache is seeded from those RPC results, lazily,
        well after POS boot (see pos_store.js::_iml_getOffline).

    Keeping this class as a no-op inherit documents the decision and gives a
    safe place to hook future server-side session logic without ever
    touching the boot-critical data-loading path.
    """
    _inherit = 'pos.session'
