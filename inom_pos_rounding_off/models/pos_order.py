# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    rounding_amount = fields.Float(
        string='Rounding Amount',
        digits=(16, 4),
        default=0.0,
        readonly=True,
        compute='_compute_rounding_from_payments',
        store=True,
    )

    @api.depends('payment_ids', 'payment_ids.amount', 'payment_ids.payment_method_id')
    def _compute_rounding_from_payments(self):
        """Payment lines se rounding amount nikalo"""
        for order in self:
            rounding_amount = 0.0
            for payment in order.payment_ids:
                if payment.payment_method_id.is_rounding_method:
                    rounding_amount = abs(payment.amount)
            order.rounding_amount = rounding_amount
