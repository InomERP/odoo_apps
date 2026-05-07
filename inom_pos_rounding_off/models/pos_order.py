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

    @api.depends('payment_ids', 'payment_ids.amount')
    def _compute_rounding_from_payments(self):
        """Payment lines se rounding amount nikalo"""
        for order in self:
            rounding_amount = 0.0
            for payment in order.payment_ids:
                if payment.payment_method_id.is_rounding_method:
                    rounding_amount = abs(payment.amount)
            order.rounding_amount = rounding_amount

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super()._order_fields(ui_order)
        return order_fields

    def _export_for_ui(self, order):
        result = super()._export_for_ui(order)
        result['rounding_amount'] = order.rounding_amount
        return result






# -*- coding: utf-8 -*-
# from odoo import models, fields, api


# class PosOrder(models.Model):
#     _inherit = 'pos.order'

#     rounding_amount = fields.Float(
#         string='Rounding Amount',
#         digits=(16, 4),
#         default=0.0,
#         readonly=True,
#     )

#     @api.model
#     def _order_fields(self, ui_order):
#         order_fields = super()._order_fields(ui_order)
#         order_fields['rounding_amount'] = ui_order.get('rounding_amount', 0.0)
#         return order_fields

#     def _export_for_ui(self, order):
#         result = super()._export_for_ui(order)
#         result['rounding_amount'] = order.rounding_amount
#         return result














# from odoo import models, fields, api


# class PosOrder(models.Model):
#     _inherit = 'pos.order'

#     rounding_amount = fields.Float(
#         string='Rounding Amount',
#         digits=(16, 4),
#         default=0.0,
#         readonly=True,
#     )

#     @api.model
#     def _order_fields(self, ui_order):
#         order_fields = super()._order_fields(ui_order)
#         order_fields['rounding_amount'] = ui_order.get('rounding_amount', 0.0)
#         return order_fields

#     def _export_for_ui(self, order):
#         result = super()._export_for_ui(order)
#         result['rounding_amount'] = order.rounding_amount
#         return result