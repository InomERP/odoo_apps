# -*- coding: utf-8 -*-
# Part of Inomerp. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    # The 'picking_ids' field used below is provided by the 'purchase_stock'
    # module, which is therefore declared as a dependency in the manifest.
    _inherit = 'purchase.order'

    has_backorder = fields.Boolean(
        string='Has Backorder',
        compute='_compute_has_backorder',
        search='_search_has_backorder',
        help="Indicates whether this purchase order still has at least one "
             "outstanding (not yet fully received) incoming backorder receipt. "
             "It becomes False automatically once every backorder receipt has "
             "been validated, so completed orders no longer show the indicator.",
    )

    @api.depends(
        'picking_ids',
        'picking_ids.backorder_id',
        'picking_ids.state',
        'picking_ids.picking_type_code',
    )
    def _compute_has_backorder(self):
        """Flag purchase orders that still have an outstanding incoming backorder.

        When an incoming receipt is only partially processed, Odoo generates a
        backorder picking whose ``backorder_id`` points to the original receipt.
        A purchase order is considered to have a backorder only while at least
        one such backorder receipt is still pending, i.e. not yet validated
        (state ``done``) and not cancelled. Once every backorder receipt has
        been fully received, the flag automatically becomes False.
        """
        closed_states = ('done', 'cancel')
        for order in self:
            order.has_backorder = any(
                picking.backorder_id
                for picking in order.picking_ids
                if picking.picking_type_code == 'incoming'
                and picking.state not in closed_states
            )

    def _search_has_backorder(self, operator, value):
        """Make the non-stored ``has_backorder`` field filterable.

        The boolean condition is resolved into a concrete domain on purchase
        orders by locating outstanding (not yet validated) incoming backorder
        receipts and mapping them back to their purchase orders, mirroring the
        logic of ``_compute_has_backorder``.
        """
        if operator not in ('=', '!='):
            raise NotImplementedError(
                _("Unsupported operator '%s' for the 'has_backorder' field.",
                  operator)
            )

        backorder_pickings = self.env['stock.picking'].search([
            ('purchase_id', '!=', False),
            ('picking_type_code', '=', 'incoming'),
            ('state', 'not in', ['done', 'cancel']),
            ('backorder_id', '!=', False),
        ])
        order_ids = backorder_pickings.purchase_id.ids

        # Resolve the (operator, value) pair to the matching orders.
        searching_for_true = (operator == '=') == bool(value)
        if searching_for_true:
            return [('id', 'in', order_ids)]
        return [('id', 'not in', order_ids)]
