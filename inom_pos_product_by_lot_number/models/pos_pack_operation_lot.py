# -*- coding: utf-8 -*-
from odoo import models


class PosPackOperationLot(models.Model):
    """
    pos.pack.operation.lot bridges a POS order line to its lot name(s).

    ROOT-CAUSE NOTE (Odoo 19):
    -------------------------
    The earlier version of this module overrode `_load_pos_data_fields`
    here and RETURNED A HARD-CODED LIST WITHOUT CALLING super()
    (it returned ['id', 'pos_order_line_id', 'lot_name']) together with a
    `_load_pos_data_domain` returning [] (which loaded EVERY pack-lot row in
    the database).

    That replaced core's curated field set (core loads
    ['lot_name', 'pos_order_line_id', 'write_date']) and dumped unrelated
    rows into the POS, malforming the relational graph that
    `processServerData` walks at startup — one of the triggers of the
    "Cannot read properties of undefined (reading 'currency_id')" crash.

    Core already loads this model with the correct fields and a domain
    scoped to the current session's lines, so we now leave loading entirely
    to core and only keep this inherit as a documented anchor point.
    """
    _inherit = 'pos.pack.operation.lot'
