# -*- coding: utf-8 -*-
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _inom_revert_done_quantities(self):
        """Reverse the on-hand impact of already validated stock moves.

        A validated move pushed quantity from its source location to its
        destination location. To undo that we add the quantity back at the
        source and remove it from the destination, restoring the warehouse to
        the state it had before the transfer was processed.
        """
        Quant = self.env['stock.quant']
        for move in self:
            for line in move.move_line_ids:
                qty = line.quantity_product_uom
                if not qty:
                    continue
                # Put the quantity back where it was taken from.
                Quant._update_available_quantity(
                    line.product_id, line.location_id, qty,
                    lot_id=line.lot_id, package_id=line.package_id,
                    owner_id=line.owner_id)
                # Remove the quantity from where it had been moved to.
                Quant._update_available_quantity(
                    line.product_id, line.location_dest_id, -qty,
                    lot_id=line.lot_id, package_id=line.package_id,
                    owner_id=line.owner_id)

    def _inom_force_cancel(self):
        """Cancel the given moves. Validated ('done') moves are reverted and
        forced to a cancelled state, while moves still in progress are dropped
        through the standard cancellation path so that reservations are
        released cleanly."""
        done_moves = self.filtered(lambda m: m.state == 'done')
        if done_moves:
            done_moves._inom_revert_done_quantities()
            done_moves.write({'state': 'cancel'})
        pending_moves = self.filtered(
            lambda m: m.state not in ('done', 'cancel'))
        if pending_moves:
            pending_moves._action_cancel()
