# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    quick_sale_type = fields.Selection(
        [
            ('regular', 'Regular'),
            ('quick_sale', 'Quick Sale'),
        ],
        string='Quick Sale Type',
        default='regular',
        copy=False,
        tracking=True,
    )

    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain=[('usage', '=', 'internal')],
        copy=False,
    )

    # =========================================================
    # CONFIG HELPERS
    # =========================================================

    _QUICK_SALE_DEFAULT_TRUE = {
        'auto_validate_delivery',
        'auto_create_invoice',
        'auto_post_invoice',
        'auto_return_delivery_on_cancel',
        'auto_cancel_invoice_on_cancel',
        'allow_partial_delivery',
    }

    def _is_enabled(self, key):
        return self.env['ir.config_parameter'].sudo().get_bool(
            'inom_quick_sale.%s' % key,
            key in self._QUICK_SALE_DEFAULT_TRUE,
        )

    # =========================================================
    # CREATE — CUSTOM SEQUENCE FOR QUICK SALE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        default_type = self.env.context.get('default_quick_sale_type')
        for vals in vals_list:
            quick_sale_type = vals.get('quick_sale_type', default_type)
            if quick_sale_type == 'quick_sale' and vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('quick.sale.order')
                    or _('New')
                )
        return super().create(vals_list)

    # =========================================================
    # CONFIRM ORDER
    # =========================================================

    def action_confirm(self):
        for order in self:
            if order.quick_sale_type != 'quick_sale':
                continue

            if not order._is_enabled('allow_negative_stock'):
                order._quick_sale_check_stock()

        result = super().action_confirm()

        for order in self:
            if order.quick_sale_type == 'quick_sale':
                order._quick_sale_post_confirm()

        return result

    def _quick_sale_check_stock(self):
        self.ensure_one()
        required = {}
        for line in self.order_line:
            product = line.product_id
            if not product or not product.is_storable:
                continue
            qty = line.product_uom_id._compute_quantity(
                line.product_uom_qty, product.uom_id)
            required[product] = required.get(product, 0.0) + qty

        if self.source_location_id:
            stock_ctx = {'location': self.source_location_id.id}
        else:
            stock_ctx = {'warehouse_id': self.warehouse_id.id}

        for product, required_qty in required.items():
            available_qty = product.with_context(**stock_ctx).free_qty
            _logger.info(
                'QUICK SALE STOCK CHECK | %s | available: %s | required: %s',
                product.display_name, available_qty, required_qty,
            )
            if product.uom_id.compare(available_qty, 0) <= 0:
                raise ValidationError(_(
                    'No stock available for product:\n\n%s'
                ) % product.display_name)
            if product.uom_id.compare(available_qty, required_qty) < 0:
                raise ValidationError(_(
                    'Not enough stock for product:\n\n%s\n\n'
                    'Available Quantity: %.2f\n'
                    'Required Quantity: %.2f'
                ) % (product.display_name, available_qty, required_qty))

    # =========================================================
    # POST CONFIRM — SET SOURCE LOCATION, TRIGGER AUTO STEPS
    # =========================================================

    def _quick_sale_post_confirm(self):
        self.ensure_one()

        outgoing_pickings = self.picking_ids.filtered(
            lambda p:
            p.picking_type_code == 'outgoing'
            and p.state not in ('done', 'cancel')
        )

        if self.source_location_id:
            for picking in outgoing_pickings:
                picking.location_id = self.source_location_id
                picking.move_ids.write({
                    'location_id': self.source_location_id.id,
                })

        if self._is_enabled('auto_validate_delivery'):
            self._quick_sale_validate_delivery()

        if self._is_enabled('auto_create_invoice'):
            self._quick_sale_create_invoice(
                auto_post=self._is_enabled('auto_post_invoice'),
            )

    # =========================================================
    # VALIDATE A SINGLE PICKING
    # =========================================================

    def _do_validate_picking(self, picking):
        allow_negative = self._is_enabled('allow_negative_stock')
        allow_partial = self._is_enabled('allow_partial_delivery')

        if picking.state == 'draft':
            picking.action_confirm()
        # Reserve whatever is available in the source location
        picking.action_assign()

        for move in picking.move_ids.filtered(
            lambda m: m.state not in ('done', 'cancel')
        ):
            demand_qty = move.product_uom_qty
            if allow_negative or not move.product_id.is_storable:
                move.quantity = demand_qty
            elif move.uom_id.compare(move.quantity, demand_qty) < 0 and not allow_partial:
                raise ValidationError(_(
                    'Not enough stock for:\n\n%s\n\n'
                    'Available: %.2f\n'
                    'Required: %.2f'
                ) % (
                    move.product_id.display_name,
                    move.quantity,
                    demand_qty,
                ))
            move.picked = True

        if all(move.uom_id.is_zero(move.quantity) for move in picking.move_ids):
            _logger.warning('QUICK SALE: nothing to deliver for %s', picking.name)
            return

        # Validate without opening the backorder wizard; the remaining
        # quantity (partial delivery) goes to a backorder.
        picking.with_context(
            skip_sms=True,
            skip_backorder=True,
        ).button_validate()
        _logger.info('QUICK SALE DELIVERY DONE | %s | state: %s', picking.name, picking.state)

    # =========================================================
    # AUTO VALIDATE DELIVERY
    # =========================================================

    def _quick_sale_validate_delivery(self):
        self.ensure_one()

        for picking in self.picking_ids.filtered(
            lambda p:
            p.picking_type_code == 'outgoing'
            and p.state not in ('done', 'cancel')
        ):
            self._do_validate_picking(picking)

    # =========================================================
    # AUTO REGISTER PAYMENT
    # =========================================================

    def _quick_sale_register_payment(self, invoices):
        self.ensure_one()

        payment_journal = self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash']),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if not payment_journal:
            _logger.warning(
                'QUICK SALE: No bank/cash journal found for company %s',
                self.company_id.name,
            )
            return

        for invoice in invoices.filtered(
            lambda inv: inv.state == 'posted' and inv.amount_residual > 0
        ):
            try:
                payment_method_line = payment_journal.inbound_payment_method_line_ids[:1]
                if not payment_method_line:
                    _logger.warning(
                        'QUICK SALE: No inbound payment method found for journal %s',
                        payment_journal.display_name,
                    )
                    continue

                payment = self.env['account.payment'].create({
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': invoice.partner_id.id,
                    'amount': invoice.amount_residual,
                    'journal_id': payment_journal.id,
                    'date': fields.Date.today(),
                    'memo': invoice.name,
                    'payment_method_line_id': payment_method_line.id,
                })
                payment.action_post()

                receivable_lines = (
                    payment.move_id.line_ids + invoice.line_ids
                ).filtered(
                    lambda l:
                    l.account_id.account_type == 'asset_receivable'
                    and not l.reconciled
                )
                receivable_lines.reconcile()

            except Exception as e:
                _logger.error('QUICK SALE PAYMENT ERROR: %s', str(e))

    # =========================================================
    # CREATE INVOICE
    # =========================================================

    def _quick_sale_create_invoice(self, auto_post=True):
        self.ensure_one()

        invoices = self.env['account.move']

        if self.invoice_status != 'to invoice':
            return invoices

        invoices = self._create_invoices()

        if auto_post:
            for inv in invoices:
                if inv.state == 'draft':
                    inv.action_post()

        if self._is_enabled('auto_register_payment'):
            self._quick_sale_register_payment(invoices)

        return invoices

    # =========================================================
    # RETURN A DONE DELIVERY
    # =========================================================

    def _quick_sale_return_picking(self, picking):
        self.ensure_one()
        return_picking = picking._create_return()
        # Return the full delivered quantity
        return_picking.action_return_all()
        return_picking.action_confirm()
        return_picking.action_assign()
        for move in return_picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        return_picking.with_context(
            skip_sms=True,
            skip_backorder=True,
        ).button_validate()
        self.message_post(
            body=_('Return Delivery %s created automatically.') % return_picking.name
        )
        return return_picking

    # =========================================================
    # CANCEL ORDER
    # =========================================================

    def action_cancel(self):
        for order in self:
            if order.quick_sale_type != 'quick_sale':
                continue

            if order._is_enabled('auto_return_delivery_on_cancel'):
                for picking in order.picking_ids.filtered(
                    lambda p:
                    p.state == 'done'
                    and p.picking_type_code == 'outgoing'
                    and not p.return_ids
                ):
                    order._quick_sale_return_picking(picking)

            if order._is_enabled('auto_cancel_invoice_on_cancel'):
                for invoice in order.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted'
                ):
                    invoice.line_ids.filtered(
                        lambda l:
                        l.account_id.account_type == 'asset_receivable'
                        and (l.matched_debit_ids or l.matched_credit_ids)
                    ).remove_move_reconcile()

                    invoice.button_draft()
                    invoice.button_cancel()
                    order.message_post(
                        body=_('Invoice %s cancelled automatically.') % invoice.name
                    )

        return super().action_cancel()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    quick_sale_order_id = fields.Many2one(
        'sale.order',
        string='Quick Sale Order',
        compute='_compute_quick_sale_order_id',
        store=True,
    )

    @api.depends('sale_id', 'sale_id.quick_sale_type')
    def _compute_quick_sale_order_id(self):
        for picking in self:
            if (
                picking.sale_id
                and picking.sale_id.quick_sale_type == 'quick_sale'
            ):
                picking.quick_sale_order_id = picking.sale_id
            else:
                picking.quick_sale_order_id = False