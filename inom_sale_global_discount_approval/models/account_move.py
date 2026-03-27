from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    
    _inherit = "account.move"

    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount')],
        string='Discount type',
        default='percent', help="Type of discount."
    )

    discount_rate = fields.Float('Discount Rate', digits=(16, 2))
    
    global_discount_amount = fields.Monetary(
        string='Discount',
        store=True,
        compute='_compute_amount',
        readonly=True
    )

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_ids.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_ids.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id'
    )
    def _compute_amount(self):
        
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0
            total_to_pay = move.amount_total
            currencies = set()

            for line in move.line_ids:
                if move.is_invoice(True):

                    if line.display_type == 'tax' or (
                        line.display_type == 'rounding' and line.tax_repartition_line_id
                    ):
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency

                    elif line.display_type in ('product', 'rounding'):
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency

                    elif line.display_type == 'payment_term':
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign

            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)

            currency = (len(currencies) == 1 and currencies.pop() or move.company_id.currency_id)

            new_pmt_state = 'not_paid' if move.move_type != 'entry' else False

            if move.is_invoice(include_receipts=True) and move.state == 'posted':

                if currency.is_zero(move.amount_residual):
                    if all(payment.is_matched for payment in move._get_reconciled_payments()):
                        new_pmt_state = 'paid'
                    else:
                        new_pmt_state = move._get_invoice_in_payment_state()

                elif currency.compare_amounts(total_to_pay, abs(total_residual)) != 0:
                    new_pmt_state = 'partial'

            if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):

                reverse_type = (
                    move.move_type == 'in_invoice' and 'in_refund'
                    or move.move_type == 'out_invoice' and 'out_refund'
                    or 'entry'
                )

                reverse_moves = self.env['account.move'].search([
                    ('reversed_entry_id', '=', move.id),
                    ('state', '=', 'posted'),
                    ('move_type', '=', reverse_type)
                ])

                reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')

                if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(
                    lambda x: x not in (
                        reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id')
                    )
                ) == move:
                    new_pmt_state = 'reversed'

            move.payment_state = new_pmt_state

    # =========================
    # 🔥 UPDATED ONCHANGE
    # =========================
    @api.onchange('discount_type','discount_rate','invoice_line_ids')
    def _supply_rate(self):

        for inv in self:

            if not inv.invoice_line_ids:
                return

            total = sum(line.quantity * line.price_unit for line in inv.invoice_line_ids)

            # =========================
            # ✅ PERCENT CASE
            # =========================
            if inv.discount_type == 'percent':

                max_discount_limit = float(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'sale_global_discount_approval.max_discount_limit', 100
                    )
                )

                if inv.discount_rate > max_discount_limit:

                    for line in inv.invoice_line_ids:
                        line.discount = 0

                    inv.global_discount_amount = 0

                    return {
                        'warning': {
                            'title': "Warning",
                            'message': f"Discount percentage cannot be greater than {max_discount_limit}%"
                        }
                    }

                total_discount = 0

                for line in inv.invoice_line_ids:
                    line.discount = inv.discount_rate
                    total_discount += (
                        line.price_unit * line.quantity * inv.discount_rate / 100
                    )

                inv.global_discount_amount = total_discount

            # =========================
            # ✅ AMOUNT CASE
            # =========================
            else:

                max_discount_amount = float(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'sale_global_discount_approval.max_discount_amount', 0
                    )
                )

                if max_discount_amount and inv.discount_rate > max_discount_amount:

                    for line in inv.invoice_line_ids:
                        line.discount = 0

                    inv.global_discount_amount = 0

                    return {
                        'warning': {
                            'title': "Warning",
                            'message': f"Discount cannot be greater than {max_discount_amount}"
                        }
                    }

                if inv.discount_rate > total:

                    for line in inv.invoice_line_ids:
                        line.discount = 0

                    inv.global_discount_amount = 0

                    return {
                        'warning': {
                            'title': "Warning",
                            'message': "Discount amount cannot be greater than Untaxed Amount"
                        }
                    }

                discount_percent = (inv.discount_rate / total) * 100 if total else 0

                for line in inv.invoice_line_ids:
                    line.discount = discount_percent

                inv.global_discount_amount = inv.discount_rate

    def button_dummy(self):
        for inv in self:
            inv._supply_rate()
        return True


class AccountInvoiceLine(models.Model):

    _inherit = "account.move.line"

    discount = fields.Float(
        string='Discount (%)',
        digits=(16, 20),
        default=0.0
    )

# from odoo import api, fields, models
# from odoo.exceptions import ValidationError


# class AccountInvoice(models.Model):
    
#     _inherit = "account.move"

#     discount_type = fields.Selection(
#         [('percent', 'Percentage'), ('amount', 'Amount')],
#         string='Discount type',
#         default='percent', help="Type of discount.")
#     discount_rate = fields.Float('Discount Rate', digits=(16, 2),)
    
#     global_discount_amount = fields.Monetary(
#     string='Discount',
#     store=True,
#     compute='_compute_amount',
#     readonly=True
#     )


    
#     @api.depends(
#         'line_ids.matched_debit_ids.debit_move_id.move_id.payment_ids.is_matched',
#         'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
#         'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
#         'line_ids.matched_credit_ids.credit_move_id.move_id.payment_ids.is_matched',
#         'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
#         'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
#         'line_ids.balance',
#         'line_ids.currency_id',
#         'line_ids.amount_currency',
#         'line_ids.amount_residual',
#         'line_ids.amount_residual_currency',
#         'line_ids.payment_id.state',
#         'line_ids.full_reconcile_id')
#     def _compute_amount(self):
        
#         for move in self:
#             print("mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm",move)
#             total_untaxed, total_untaxed_currency = 0.0, 0.0
#             total_tax, total_tax_currency = 0.0, 0.0
#             total_residual, total_residual_currency = 0.0, 0.0
#             total, total_currency = 0.0, 0.0
#             total_to_pay = move.amount_total
#             currencies = set()
#             for line in move.line_ids:
#                 print("lllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllllll",line)
#                 if move.is_invoice(True):
                    
#                     if line.display_type == 'tax' or (
#                             line.display_type == 'rounding' and
#                             line.tax_repartition_line_id):
                        
#                         total_tax += line.balance
#                         total_tax_currency += line.amount_currency
#                         total += line.balance
#                         total_currency += line.amount_currency
#                     elif line.display_type in ('product', 'rounding'):
                    
#                         total_untaxed += line.balance
#                         total_untaxed_currency += line.amount_currency
#                         total += line.balance
#                         total_currency += line.amount_currency
#                     elif line.display_type == 'payment_term':
                        
#                         total_residual += line.amount_residual
#                         total_residual_currency += line.amount_residual_currency
#                 else:
                    
#                     if line.debit:
#                         total += line.balance
#                         total_currency += line.amount_currency
#             sign = move.direction_sign
#             move.amount_untaxed = sign * (total_untaxed_currency if len(
#                 currencies) == 1 else total_untaxed)
#             move.amount_tax = sign * (
#                 total_tax_currency if len(currencies) == 1 else total_tax)
#             move.amount_total = sign * total_currency
#             move.amount_residual = -sign * total_residual_currency
#             move.amount_untaxed_signed = -total_untaxed
#             move.amount_tax_signed = -total_tax
#             move.amount_total_signed = abs(
#                 total) if move.move_type == 'entry' else -total
#             move.amount_residual_signed = total_residual
#             move.amount_total_in_currency_signed = abs(
#                 move.amount_total) if move.move_type == 'entry' else -(
#                     sign * move.amount_total)
#             currency = (len(
#                 currencies) == 1 and currencies.pop() or
#                         move.company_id.currency_id)
#             new_pmt_state = 'not_paid' if move.move_type != 'entry' else False
#             if move.is_invoice(
#                     include_receipts=True) and move.state == 'posted':
#                 if currency.is_zero(move.amount_residual):
#                     if all(payment.is_matched for payment in
#                            move._get_reconciled_payments()):
#                         new_pmt_state = 'paid'
#                     else:
#                         new_pmt_state = move._get_invoice_in_payment_state()
#                 elif currency.compare_amounts(total_to_pay,
#                                               abs(total_residual)) != 0:
#                     new_pmt_state = 'partial'
#             if new_pmt_state == 'paid' and move.move_type in (
#                     'in_invoice', 'out_invoice', 'entry'):
#                 reverse_type = (move.move_type == 'in_invoice' and 'in_refund'
#                                 or move.move_type == 'out_invoice' and
#                                 'out_refund' or 'entry')
#                 reverse_moves = self.env['account.move'].search(
#                     [('reversed_entry_id', '=', move.id),
#                      ('state', '=', 'posted'),
#                      ('move_type', '=', reverse_type)])
               
#                 reverse_moves_full_recs = reverse_moves.mapped(
#                     'line_ids.full_reconcile_id')
#                 if reverse_moves_full_recs.mapped(
#                         'reconciled_line_ids.move_id').filtered(
#                     lambda x: x not in (
#                             reverse_moves + reverse_moves_full_recs.mapped(
#                         'exchange_move_id'))) == move:
#                     new_pmt_state = 'reversed'
#             move.payment_state = new_pmt_state

#     @api.onchange('discount_type','discount_rate','invoice_line_ids')
#     def _supply_rate(self):

#         for inv in self:

#             if not inv.invoice_line_ids:
#                 return

#             total = sum(line.quantity * line.price_unit for line in inv.invoice_line_ids)

        
#             if inv.discount_type == 'percent':

#                 if inv.discount_rate > 100:

                    
#                     for line in inv.invoice_line_ids:
#                         line.discount = 0

#                     inv.global_discount_amount = 0

#                     return {
#                         'warning': {
#                             'title': "Warning",
#                             'message': "Discount percentage cannot be greater than 100%"
#                         }
#                     }

#                 total_discount = 0

#                 for line in inv.invoice_line_ids:

#                     line.discount = inv.discount_rate

#                     total_discount += (
#                         line.price_unit * 
#                         line.quantity * 
#                         inv.discount_rate / 100
#                     )

#                 inv.global_discount_amount = total_discount

            
#             else:

#                 if inv.discount_rate > total:

#                     for line in inv.invoice_line_ids:
#                         line.discount = 0

#                     inv.global_discount_amount = 0

#                     return {
#                         'warning': {
#                             'title': "Warning",
#                             'message': "Discount amount cannot be greater than Untaxed Amount"
#                         }
#                     }

#                 discount_percent = 0

#                 if total:
#                     discount_percent = (inv.discount_rate / total) * 100

#                 for line in inv.invoice_line_ids:

#                     line.discount = discount_percent

#                 inv.global_discount_amount = inv.discount_rate


            
#     def button_dummy(self):
#         for inv in self:
#             inv._supply_rate()
#         return True


# class AccountInvoiceLine(models.Model):

#     _inherit = "account.move.line"
#     discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0,
#                             help="Give the discount needed")















