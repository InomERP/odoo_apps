# -*- coding: utf-8 -*-
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _inom_get_forced_kit_bom(self):
        """Return the Kit (phantom) BoM selected on the related sale line.

        Returns an empty ``mrp.bom`` recordset when no applicable Kit BoM is
        selected for this move's product.
        """
        self.ensure_one()
        bom = self.sale_line_id.bom_id
        if not bom or bom.type != 'phantom':
            return self.env['mrp.bom']
        if bom.product_id:
            applies = bom.product_id == self.product_id
        else:
            applies = bom.product_tmpl_id == self.product_id.product_tmpl_id
        return bom if applies else self.env['mrp.bom']

    def _action_explode(self):
        """Explode Kit moves using the BoM chosen on the Sale Order line.

        Moves whose sale line carries a Kit (phantom) BoM are exploded against
        that exact BoM (via the ``inom_forced_kit_bom_id`` context, honoured by
        ``mrp.bom._bom_find``). All other moves keep the standard Odoo
        explosion behaviour.
        """
        forced_moves = self.browse()
        standard_moves = self.browse()
        for move in self:
            if move._inom_get_forced_kit_bom():
                forced_moves |= move
            else:
                standard_moves |= move

        result = self.browse()
        if standard_moves:
            result |= super(StockMove, standard_moves)._action_explode()
        for move in forced_moves:
            forced_bom = move._inom_get_forced_kit_bom()
            result |= super(
                StockMove,
                move.with_context(inom_forced_kit_bom_id=forced_bom.id),
            )._action_explode()
        return result
