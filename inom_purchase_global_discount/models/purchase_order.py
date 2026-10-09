from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Fixed Amount')],
        string="Global Discount Type",
    )

    discount_rate = fields.Float(
        string="Global Discount",
    )

    global_discount_amount = fields.Monetary(
        string="Global Discount Amount",
        compute="_compute_global_discount",
        store=True,
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_discount_limits(self):
        # sudo(): system parameters are not readable by ordinary purchase
        # users, but the configured limits must apply to every user.
        param = self.env['ir.config_parameter'].sudo()

        # Odoo 20: get_param() was replaced by typed getters; a missing or
        # blank parameter returns the default (0.0 = no limit).
        max_percent = param.get_float(
            'purchase_global_discount.max_discount_limit', 0.0,
        )
        max_amount = param.get_float(
            'purchase_global_discount.max_discount_amount', 0.0,
        )

        return max_percent, max_amount

    def _get_lines_total(self):
        """Sum of price_unit * quantity over the order lines.

        Section / note lines carry no price nor quantity, so they add 0.
        """
        self.ensure_one()
        return sum(
            line.price_unit * line.product_qty
            for line in self.order_line
        )

    # ------------------------------------------------------------------
    # Computes & constraints
    # ------------------------------------------------------------------
    @api.depends(
        'order_line.product_qty',
        'order_line.price_unit',
        'discount_type',
        'discount_rate',
    )
    def _compute_global_discount(self):
        for order in self:
            total = order._get_lines_total()

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
            if order.discount_type == 'percent':
                if max_percent > 0 and order.discount_rate > max_percent:
                    raise ValidationError(self.env._(
                        "Maximum allowed discount is %s%%", max_percent,
                    ))

            elif order.discount_type == 'amount':
                if order.discount_rate > order._get_lines_total():
                    raise ValidationError(self.env._(
                        "Discount cannot exceed untaxed amount",
                    ))

                if max_amount > 0 and order.discount_rate > max_amount:
                    raise ValidationError(self.env._(
                        "Maximum allowed discount is %s", max_amount,
                    ))

    # ------------------------------------------------------------------
    # Discount distribution on lines
    # ------------------------------------------------------------------
    def _apply_global_discount_to_lines(self):
        discount_precision = self.env['decimal.precision'].precision_get(
            'Discount'
        )

        for order in self:
            # Section / note lines never get a discount.
            lines = order.order_line.filtered(lambda l: not l.display_type)
            if not lines:
                continue

            total = order._get_lines_total()
            if total <= 0:
                continue

            if order.discount_type == 'percent':
                new_discounts = {
                    line: order.discount_rate for line in lines
                }

            elif order.discount_type == 'amount':
                new_discounts = {}
                for line in lines:
                    line_total = line.price_unit * line.product_qty

                    if not line_total:
                        new_discounts[line] = 0
                        continue

                    share = order.discount_rate * line_total / total
                    percent = (share / line_total) * 100
                    new_discounts[line] = round(percent, 4)

            else:
                continue

            for line, value in new_discounts.items():
                # Skip no-op writes: avoids useless recomputes of the
                # line subtotals/taxes on every order write.
                if float_compare(
                    line.discount, value, precision_digits=discount_precision,
                ):
                    line.discount = value

    @api.onchange(
        'discount_type',
        'discount_rate',
        'order_line',
    )
    def _onchange_discount(self):
        max_percent, max_amount = self._get_discount_limits()
        total = self._get_lines_total()

        if self.discount_type == 'percent':
            if max_percent > 0 and self.discount_rate > max_percent:
                self.discount_rate = 0
                return {
                    'warning': {
                        'title': self.env._("Warning"),
                        'message': self.env._(
                            "Maximum allowed discount is %s%%", max_percent,
                        ),
                    }
                }

        if self.discount_type == 'amount':
            if max_amount > 0 and self.discount_rate > max_amount:
                self.discount_rate = 0
                return {
                    'warning': {
                        'title': self.env._("Warning"),
                        'message': self.env._(
                            "Maximum allowed discount is %s", max_amount,
                        ),
                    }
                }

            if self.discount_rate > total:
                self.discount_rate = 0
                return {
                    'warning': {
                        'title': self.env._("Warning"),
                        'message': self.env._(
                            "Discount cannot exceed untaxed amount",
                        ),
                    }
                }

        self._apply_global_discount_to_lines()

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._apply_global_discount_to_lines()
        return orders

    def write(self, vals):
        res = super().write(vals)
        self._apply_global_discount_to_lines()
        return res

    def button_confirm(self):
        self._apply_global_discount_to_lines()
        return super().button_confirm()
