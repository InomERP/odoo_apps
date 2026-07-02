# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Inverse of account.move.line.receipt_move_id. Lets us know which vendor
    # bill lines were generated from this received move.
    receipt_bill_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='receipt_move_id',
        string='Generated Bill Lines',
    )
    qty_billed = fields.Float(
        string='Billed Quantity',
        compute='_compute_qty_billed',
        store=True,
        digits='Product Unit of Measure',
        help='Received quantity of this move that has already been billed to '
             'the vendor through the "Bill from Receipts" wizard.',
    )

    @api.depends(
        'receipt_bill_line_ids.quantity',
        'receipt_bill_line_ids.parent_state',
        'receipt_bill_line_ids.move_id.move_type',
    )
    def _compute_qty_billed(self):
        for move in self:
            billed = 0.0
            for line in move.receipt_bill_line_ids:
                if line.parent_state == 'cancel':
                    continue
                if line.move_id.move_type == 'in_invoice':
                    billed += line.quantity
                elif line.move_id.move_type == 'in_refund':
                    billed -= line.quantity
            move.qty_billed = billed