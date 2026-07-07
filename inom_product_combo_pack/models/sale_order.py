# -*- coding: utf-8 -*-
from odoo import _, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_open_pack_wizard(self):
        self.ensure_one()
        return self._open_pack_wizard(explode=False)

    def action_open_exploded_pack_wizard(self):
        self.ensure_one()
        return self._open_pack_wizard(explode=True)

    def _open_pack_wizard(self, explode=False):
        return {
            'name': _('Add Combo Pack'),
            'type': 'ir.actions.act_window',
            'res_model': 'combo.pack.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_model': 'sale.order',
                'default_order_id': self.id,
                'default_explode': explode,
            },
        }
