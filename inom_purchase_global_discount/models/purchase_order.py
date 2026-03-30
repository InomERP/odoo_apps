from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Fixed Amount')],
        string="Global Discount Type"
    )

    discount_rate = fields.Float(
        string="Global Discount"
    )

    global_discount_amount = fields.Monetary(
        string="Global Discount Amount",
        compute="_compute_global_discount",
        store=True
    )

    
    def _get_discount_limits(self):

        param = self.env['ir.config_parameter'].sudo()

        max_percent = param.get_param(
            'purchase_global_discount.max_discount_limit'
        )

        max_amount = param.get_param(
            'purchase_global_discount.max_discount_amount'
        )

        max_percent = float(max_percent) if max_percent else 0
        max_amount = float(max_amount) if max_amount else 0

        return max_percent, max_amount

    
    @api.depends(
        'order_line.product_qty',
        'order_line.price_unit',
        'discount_type',
        'discount_rate'
    )
    def _compute_global_discount(self):

        for order in self:

            total = sum(
                line.price_unit * line.product_qty
                for line in order.order_line
            )

            if order.discount_type == 'percent':

                order.global_discount_amount = (
                    total * order.discount_rate / 100
                )

            elif order.discount_type == 'amount':

                order.global_discount_amount = order.discount_rate

            else:
                order.global_discount_amount = 0.0

    
    @api.constrains('discount_type', 'discount_rate', 'order_line')
    def _check_discount(self):

        max_percent, max_amount = self._get_discount_limits()

        for order in self:

            total = sum(
                line.price_unit * line.product_qty
                for line in order.order_line
            )

            if order.discount_type == 'percent':
                print("...........................................................",order.discount_type)

                if max_percent > 0 and order.discount_rate > max_percent:

                    raise ValidationError(
                        f"Maximum allowed discount is {max_percent}%"
                    )

            elif order.discount_type == 'amount':

                if order.discount_rate > total:

                    raise ValidationError(
                        "Discount cannot exceed untaxed amount"
                    )

                if max_amount > 0 and order.discount_rate > max_amount:

                    raise ValidationError(
                        f"Maximum allowed discount is {max_amount}"
                    )

    
    def _apply_global_discount_to_lines(self):

        for order in self:

            if not order.order_line:
                continue

            total = sum(
                line.price_unit * line.product_qty
                for line in order.order_line
            )

            if total <= 0:
                continue

            if order.discount_type == 'percent':

                for line in order.order_line:
                    line.discount = order.discount_rate

            elif order.discount_type == 'amount':

                for line in order.order_line:

                    line_total = (
                        line.price_unit * line.product_qty
                    )

                    if not line_total:

                        line.discount = 0
                        continue

                    share = (
                        order.discount_rate * line_total / total
                    )

                    percent = (
                        share / line_total
                    ) * 100

                    line.discount = round(percent, 4)

    
    @api.onchange(
        'discount_type',
        'discount_rate',
        'order_line',
        'order_line.price_unit',
        'order_line.product_qty'
    )
    def _onchange_discount(self):

        max_percent, max_amount = self._get_discount_limits()

        total = sum(
            line.price_unit * line.product_qty
            for line in self.order_line
        )

        if self.discount_type == 'percent':

            if max_percent > 0 and self.discount_rate > max_percent:

                self.discount_rate = 0

                return {
                    'warning': {
                        'title': "Warning",
                        'message': f"Maximum allowed discount is {max_percent}%"
                    }
                }

        if self.discount_type == 'amount':

            if max_amount > 0 and self.discount_rate > max_amount:

                self.discount_rate = 0

                return {
                    'warning': {
                        'title': "Warning",
                        'message': f"Maximum allowed discount is {max_amount}"
                    }
                }

            if self.discount_rate > total:

                self.discount_rate = 0

                return {
                    'warning': {
                        'title': "Warning",
                        'message': "Discount cannot exceed untaxed amount"
                    }
                }

        self._apply_global_discount_to_lines()

    
    @api.model
    def create(self, vals):

        order = super().create(vals)

        order._apply_global_discount_to_lines()

        return order

    
    def write(self, vals):

        res = super().write(vals)

        for order in self:
            order._apply_global_discount_to_lines()

        return res

    
    def button_confirm(self):

        self._apply_global_discount_to_lines()

        return super().button_confirm()

