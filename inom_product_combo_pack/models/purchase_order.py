# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_open_pack_wizard(self):
        self.ensure_one()
        self._check_purchase_pack_enabled()
        return self._open_pack_wizard(explode=False)

    def action_open_exploded_pack_wizard(self):
        self.ensure_one()
        self._check_purchase_pack_enabled()
        return self._open_pack_wizard(explode=True)

    def _check_purchase_pack_enabled(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'inom_product_combo_pack.allow_pack_on_purchase'
        )
        if enabled not in ('True', 'true', '1'):
            raise UserError(_(
                'Combo packs on purchase orders are disabled. Enable '
                '"Allow Combo Pack on Purchase" in the Purchase settings first.'
            ))

    def _open_pack_wizard(self, explode=False):
        return {
            'name': _('Add Combo Pack'),
            'type': 'ir.actions.act_window',
            'res_model': 'combo.pack.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_model': 'purchase.order',
                'default_order_id': self.id,
                'default_explode': explode,
            },
        }
