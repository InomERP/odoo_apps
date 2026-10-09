# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderMergeLinesWizard(models.TransientModel):
    """Phase 5: a small confirmation wizard, opened from the 'Merge Order
    Lines' item in the sale order's Action (cog) menu, that merges duplicate
    product lines on that single order (summing quantity). The actual merge
    logic lives on sale.order itself so it can also be reused by the Phase 6
    auto-merge-on-save behaviour.
    """
    _name = 'sale.order.merge.lines.wizard'
    _description = 'Merge Sale Order Lines Wizard'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        default=lambda self: self.env.context.get('active_id'),
        required=True,
    )

    def action_merge(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("No sale order found to merge lines on."))
        self.sale_order_id.action_merge_order_lines()
        return {'type': 'ir.actions.act_window_close'}
