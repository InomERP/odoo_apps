from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    discount_type = fields.Selection([
        ('percent', 'Percentage'),
        ('amount', 'Fixed Amount')
    ], string="Global Discount Type")

    discount_rate = fields.Float(string="Global Discount")

    global_discount_amount = fields.Monetary(
        string="Global Discount Amount",
        compute="_compute_global_discount",
        store=True
    )

    # ===============================
    # COMPUTE DISCOUNT AMOUNT
    # ===============================
    @api.depends(
        'order_line.price_subtotal',
        'discount_type',
        'discount_rate'
    )
    def _compute_global_discount(self):

        for order in self:

            untaxed_total = sum(
                order.order_line.mapped('price_subtotal')
            )

            if order.discount_type == 'percent':

                order.global_discount_amount = (
                    untaxed_total * order.discount_rate / 100
                )

            elif order.discount_type == 'amount':

                order.global_discount_amount = order.discount_rate

            else:
                order.global_discount_amount = 0.0


    # ===============================
    # VALIDATION (SETTINGS BASED)
    # ===============================
    @api.constrains('discount_type','discount_rate','order_line')
    def _check_discount(self):

        param = self.env['ir.config_parameter'].sudo()

        max_percent = float(
            param.get_param(
                'sale_global_discount_approval.max_discount_limit',0
            )
        )

        max_amount = float(
            param.get_param(
                'sale_global_discount_approval.max_discount_amount',0
            )
        )

        for order in self:

            untaxed_total = sum(
                order.order_line.mapped('price_subtotal')
            )

            # Percentage validation
            if order.discount_type == 'percent':

                if max_percent and order.discount_rate > max_percent:

                    raise ValidationError(
                        f"Discount cannot be greater than {max_percent}%"
                    )

            # Amount validation
            elif order.discount_type == 'amount':

                if order.discount_rate > untaxed_total:

                    raise ValidationError(
                        "Discount amount cannot be greater than Untaxed Amount"
                    )

                if max_amount and order.discount_rate > max_amount:

                    raise ValidationError(
                        f"Discount cannot be greater than {max_amount}"
                    )


    # ===============================
    # APPLY DISCOUNT ON LINES
    # ===============================
    def _apply_global_discount_to_lines(self):

        for order in self:

            if not order.order_line:
                continue

            untaxed_total = sum(
                order.order_line.mapped('price_subtotal')
            )

            if untaxed_total <= 0:
                continue

            # Percentage
            if order.discount_type == 'percent':

                for line in order.order_line:

                    line.discount = order.discount_rate


            # Amount
            elif order.discount_type == 'amount':

                if order.discount_rate > untaxed_total:

                    raise ValidationError(
                        "Discount amount cannot be greater than Untaxed Amount"
                    )

                for line in order.order_line:

                    line_total = line.price_subtotal

                    if not line_total:
                        line.discount = 0
                        continue

                    line_discount_amount = (
                        order.discount_rate *
                        line_total /
                        untaxed_total
                    )

                    percent = (
                        line_discount_amount /
                        line_total
                    ) * 100

                    line.discount = round(percent,4)


    # ===============================
    # ONCHANGE (UI)
    # ===============================
    @api.onchange(
        'discount_type',
        'discount_rate',
        'order_line',
        'order_line.price_unit',
        'order_line.product_uom_qty'
    )
    def _onchange_discount(self):

        param = self.env['ir.config_parameter'].sudo()

        max_percent = float(
            param.get_param(
                'sale_global_discount_approval.max_discount_limit',0
            )
        )

        max_amount = float(
            param.get_param(
                'sale_global_discount_approval.max_discount_amount',0
            )
        )

        untaxed_total = sum(
            self.order_line.mapped('price_subtotal')
        )

        # Percent validation
        if self.discount_type == 'percent':

            if max_percent and self.discount_rate > max_percent:

                self.discount_rate = 0

                return {
                    'warning':{
                        'title':"Warning",
                        'message':f"Discount cannot be greater than {max_percent}%"
                    }
                }

        # Amount validation
        if self.discount_type == 'amount':

            if max_amount and self.discount_rate > max_amount:

                self.discount_rate = 0

                return {
                    'warning':{
                        'title':"Warning",
                        'message':f"Discount cannot be greater than {max_amount}"
                    }
                }

            if self.discount_rate > untaxed_total:

                self.discount_rate = 0

                return {
                    'warning':{
                        'title':"Warning",
                        'message':"Discount cannot be greater than Untaxed Amount"
                    }
                }

        self._apply_global_discount_to_lines()


    # ===============================
    # CREATE
    # ===============================
    @api.model
    def create(self,vals):

        order = super().create(vals)

        order._apply_global_discount_to_lines()

        return order


    # ===============================
    # WRITE
    # ===============================
    def write(self,vals):

        res = super().write(vals)

        for order in self:

            order._apply_global_discount_to_lines()

        return res


    # ===============================
    # CONFIRM SAFETY
    # ===============================
    def action_confirm(self):

        self._apply_global_discount_to_lines()

        return super().action_confirm()



# from odoo import models, fields, api
# from odoo.exceptions import ValidationError


# class SaleOrder(models.Model):
#     _inherit = "sale.order"

#     discount_type = fields.Selection([
#         ('percent', 'Percentage'),
#         ('amount', 'Fixed Amount')
#     ], string="Global Discount Type")

#     discount_rate = fields.Float(string="Global Discount")

#     global_discount_amount = fields.Monetary(
#         string="Global Discount Amount",
#         compute="_compute_global_discount",
#         store=True
#     )

    
#     @api.depends(
#         'order_line.product_uom_qty',
#         'order_line.price_unit',
#         'discount_type',
#         'discount_rate'
#     )
#     def _compute_global_discount(self):
#         for order in self:

#             untaxed_total = sum(
#                 line.price_unit * line.product_uom_qty
#                 for line in order.order_line
#             )

#             if order.discount_type == 'percent':
#                 order.global_discount_amount = (
#                     untaxed_total * order.discount_rate / 100
#                 )

#             elif order.discount_type == 'amount':
#                 order.global_discount_amount = order.discount_rate

#             else:
#                 order.global_discount_amount = 0.0


    
#     @api.constrains('discount_type', 'discount_rate', 'order_line')
#     def _check_discount(self):

#         param = self.env['ir.config_parameter'].sudo()

#         max_percent = float(param.get_param(
#             'sale_global_discount_approval.max_discount_limit', 0
#         ))

#         max_amount = float(param.get_param(
#             'sale_global_discount_approval.max_discount_amount', 0
#         ))

#         for order in self:

#             untaxed_total = sum(
#                 line.price_unit * line.product_uom_qty
#                 for line in order.order_line
#             )

#             # Percentage validation
#             if order.discount_type == 'percent':

#                 if max_percent and order.discount_rate > max_percent:
#                     raise ValidationError(
#                         f"Discount cannot be greater than {max_percent}%"
#                     )

#             # Amount validation
#             elif order.discount_type == 'amount':

#                 if order.discount_rate > untaxed_total:
#                     raise ValidationError(
#                         "Discount amount cannot be greater than Untaxed Amount"
#                     )

#                 if max_amount and order.discount_rate > max_amount:
#                     raise ValidationError(
#                         f"Discount cannot be greater than {max_amount}"
#                     )


    
#     def _apply_global_discount_to_lines(self):

#         for order in self:

#             if not order.order_line:
#                 continue

#             untaxed_total = sum(
#                 line.price_unit * line.product_uom_qty
#                 for line in order.order_line
#             )

#             # Percentage
#             if order.discount_type == 'percent':

#                 for line in order.order_line:
#                     line.discount = order.discount_rate

#             # Amount
#             elif order.discount_type == 'amount':

#                 if order.discount_rate > untaxed_total:
#                     raise ValidationError(
#                         "Discount amount cannot be greater than Untaxed Amount"
#                     )

#                 for line in order.order_line:

#                     line_total = line.price_unit * line.product_uom_qty

#                     if untaxed_total:

#                         line_discount_amount = (
#                             order.discount_rate * line_total / untaxed_total
#                         )

#                         percent = (line_discount_amount / line_total) * 100

#                         line.discount = round(percent, 6)


    
#     @api.onchange('discount_type', 'discount_rate', 'order_line')
#     def _onchange_discount(self):

#         param = self.env['ir.config_parameter'].sudo()

#         max_percent = float(param.get_param(
#             'sale_global_discount_approval.max_discount_limit', 0
#         ))

#         if self.discount_type == 'percent' and max_percent and self.discount_rate > max_percent:

#             self.discount_rate = 0

#             return {
#                 'warning': {
#                     'title': "Warning",
#                     'message': f"Discount cannot be greater than {max_percent}%"
#                 }
#             }

#         self._apply_global_discount_to_lines()


    
#     @api.model
#     def create(self, vals):
#         order = super().create(vals)
#         order._apply_global_discount_to_lines()
#         return order



#     def write(self, vals):
#         res = super().write(vals)
#         for order in self:
#             order._apply_global_discount_to_lines()
#         return res


    
#     def action_confirm(self):
#         for order in self:
#             order._apply_global_discount_to_lines()
#         return super().action_confirm()







# from odoo import models, fields, api
# from odoo.exceptions import ValidationError


# class SaleOrder(models.Model):
#     _inherit = "sale.order"

#     discount_type = fields.Selection([
#         ('percent', 'Percentage'),
#         ('amount', 'Fixed Amount')
#     ], string="Global Discount Type")

#     discount_rate = fields.Float(string="Global Discount")

#     global_discount_amount = fields.Monetary(
#         string="Global Discount Amount",
#         compute="_compute_global_discount",
#         store=True
#     )


#     @api.depends(
#         'order_line.product_uom_qty',
#         'order_line.price_unit',
#         'discount_type',
#         'discount_rate'
#     )
#     def _compute_global_discount(self):

#         for order in self:

#             untaxed_total = sum(
#                 line.price_unit * line.product_uom_qty
#                 for line in order.order_line
#             )
#             print("...............................................................",untaxed_total)

#             if order.discount_type == 'percent':
#                 print(".................................................................",order.discount_type)

#                 order.global_discount_amount = (
#                     untaxed_total * order.discount_rate / 100
#                 )

#             elif order.discount_type == 'amount':

#                 order.global_discount_amount = order.discount_rate
#                 print("..................................................................",order.global_discount_amount)

#             else:

#                 order.global_discount_amount = 0.0


    
#     @api.constrains('discount_type','discount_rate','order_line')
#     def _check_discount(self):

#         for order in self:

#             untaxed_total = sum(
#                 line.price_unit * line.product_uom_qty
#                 for line in order.order_line
#             )
#             print(".................................................................",untaxed_total)

#             if order.discount_type == 'percent':

#                 if order.discount_rate > 100:

#                     raise ValidationError(
#                         "Discount percentage cannot be greater than 100%"
#                     )

#             elif order.discount_type == 'amount':

#                 if order.discount_rate > untaxed_total:

#                     raise ValidationError(
#                         "Discount amount cannot be greater than Untaxed Amount"
#                     )


#     def _apply_global_discount_to_lines(self):

#         for order in self:

#             if not order.order_line:
#                 continue

#             untaxed_total = sum(
#                 line.price_unit * line.product_uom_qty
#                 for line in order.order_line
#             )
#             print("................................................................",untaxed_total)

            
#             if order.discount_type == 'percent':

#                 for line in order.order_line:

#                     line.discount = order.discount_rate


            
#             elif order.discount_type == 'amount':

#                 if order.discount_rate > untaxed_total:

#                     raise ValidationError(
#                         "Discount amount cannot be greater than Untaxed Amount"
#                     )

#                 for line in order.order_line:

#                     line_total = line.price_unit * line.product_uom_qty

#                     if untaxed_total:

#                         line_discount_amount = (
#                             order.discount_rate *
#                             line_total /
#                             untaxed_total
#                         )

#                         percent = (
#                             line_discount_amount /
#                             line_total
#                         ) * 100

#                         line.discount = round(percent,6)


#     @api.onchange('discount_type','discount_rate')
#     def _onchange_discount(self):

#         if self.discount_type == 'percent' and self.discount_rate > 100:

#             self.discount_rate = 0

#             return {
#                 'warning': {
#                     'title': "Warning",
#                     'message':
#                     "Discount percentage cannot be greater than 100%"
#                 }
#             }

#         self._apply_global_discount_to_lines()


#     @api.model
#     def create(self, vals):

#         order = super().create(vals)
#         print("...................................................................",order)

#         order._apply_global_discount_to_lines()

#         return order


#     def write(self, vals):

#         res = super().write(vals)
#         print(".........................................................................",res)

#         self._apply_global_discount_to_lines()

#         return res



