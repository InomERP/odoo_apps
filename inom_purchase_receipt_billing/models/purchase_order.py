# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    has_billable_receipt = fields.Boolean(
        string='Has Billable Receipt',
        compute='_compute_has_billable_receipt',
        help='Technical flag: True when at least one validated receipt still '
             'has a received quantity that has not been billed yet.',
    )

    @api.depends(
        'picking_ids.state',
        'picking_ids.picking_type_id.code',
        'picking_ids.move_ids.state',
        'picking_ids.move_ids.quantity',
        'picking_ids.move_ids.qty_billed',
        'picking_ids.move_ids.purchase_line_id',
    )
    def _compute_has_billable_receipt(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for order in self:
            order.has_billable_receipt = bool(
                order._get_billable_receipt_moves(precision))

    def _get_billable_receipt_moves(self, precision=None):
        """Return the validated incoming moves of these orders that still have
        a received quantity left to bill."""
        if precision is None:
            precision = self.env['decimal.precision'].precision_get(
                'Product Unit of Measure')
        moves = self.env['stock.move']
        for order in self:
            done_receipts = order.picking_ids.filtered(
                lambda p: p.state == 'done'
                and p.picking_type_id.code == 'incoming')
            for move in done_receipts.move_ids:
                if move.state != 'done' or not move.purchase_line_id:
                    continue
                remaining = move.quantity - move.qty_billed
                if float_compare(remaining, 0.0,
                                 precision_digits=precision) > 0:
                    moves |= move
        return moves

    def action_open_receipt_bill_wizard(self):
        """Open the receipt selection wizard for the current order(s).

        Works for a single order (form button) or several orders selected in
        the list view, provided they share the same vendor.
        """
        if not self:
            raise UserError(_('Please select at least one purchase order.'))
        vendors = self.mapped('partner_id')
        if len(vendors) > 1:
            raise UserError(_(
                'The selected purchase orders must belong to the same vendor '
                'to be billed together.'))
        if not self._get_billable_receipt_moves():
            raise UserError(_(
                'There is no validated receipt left to bill for the selected '
                'purchase order(s).'))
        return {
            'name': _('Create Bill from Receipts'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.receipt.bill.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'purchase.order',
                'active_ids': self.ids,
                'active_id': self.id if len(self) == 1 else False,
            },
        }
