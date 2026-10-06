# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _inom_force_cancel(self):
        """Force cancel transfers linked to an order, including validated
        ('done') ones.

        The transfer status is computed from its moves, so cancelling every
        move automatically drops the transfer to a 'Cancelled' state while the
        stock is returned to its original location.
        """
        for picking in self.filtered(lambda p: p.state != 'cancel'):
            picking.move_ids._inom_force_cancel()
