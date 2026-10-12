# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Provenance link: which received stock move this bill line was created from.
    # Used to compute the already-billed quantity per receipt and to keep that
    # figure self-correcting when a bill is deleted, cancelled or refunded.
    receipt_move_id = fields.Many2one(
        comodel_name='stock.move',
        string='Source Receipt Move',
        ondelete='set null',
        index=True,
        copy=False,
    )

    def _copy_data_extend_business_fields(self, values):
        # Keep the receipt link on credit notes / reversals so that refunding
        # a bill gives the quantity back to the receipt.
        super()._copy_data_extend_business_fields(values)
        values['receipt_move_id'] = self.receipt_move_id.id