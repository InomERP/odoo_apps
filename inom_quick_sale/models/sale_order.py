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

    def _get_config(self, key, default=None):
        if default is None:
            default = 'True' if key in self._QUICK_SALE_DEFAULT_TRUE else 'False'
        return self.env['ir.config_parameter'].sudo().get_param(
            'inom_quick_sale.%s' % key,
            default=default,
        )

    def _is_enabled(self, key):
        return str(self._get_config(key)).lower() in ('true', '1')

    # =========================================================
    # CREATE — CUSTOM SEQUENCE FOR QUICK SALE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('quick_sale_type') == 'quick_sale':
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
                for line in order.order_line:
                    product = line.product_id
                    if not product or product.type == 'service':
                        continue

                    available_qty = product.free_qty
                    _logger.info(
                        'QUICK SALE STOCK CHECK | %s | available: %s | required: %s',
                        product.display_name,
                        available_qty,
                        line.product_uom_qty,
                    )

                    if available_qty <= 0:
                        raise ValidationError(_(
                            'No stock available for product:\n\n%s'
                        ) % product.display_name)

                    if available_qty < line.product_uom_qty:
                        raise ValidationError(_(
                            'Not enough stock for product:\n\n%s\n\n'
                            'Available Quantity: %.2f\n'
                            'Required Quantity: %.2f'
                        ) % (
                            product.display_name,
                            available_qty,
                            line.product_uom_qty,
                        ))

        result = super().action_confirm()

        for order in self:
            if order.quick_sale_type == 'quick_sale':
                order._quick_sale_post_confirm()

        return result

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

        # Ensure stock is reserved
        if picking.state in ('confirmed', 'waiting', 'partially_available', 'assigned'):
            picking.action_assign()

        for move in picking.move_ids.filtered(
            lambda m: m.state not in ('done', 'cancel')
        ):
            demand_qty = move.product_uom_qty
            available_qty = move.product_id.free_qty

            if not allow_negative and available_qty < demand_qty:
                if not allow_partial:
                    raise ValidationError(_(
                        'Not enough stock for:\n\n%s\n\n'
                        'Available: %.2f\n'
                        'Required: %.2f'
                    ) % (
                        move.product_id.display_name,
                        available_qty,
                        demand_qty,
                    ))
                demand_qty = available_qty

            if not move.move_line_ids:
                self.env['stock.move.line'].create({
                    'move_id': move.id,
                    'picking_id': picking.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'quantity': demand_qty,
                })
            else:
                for ml in move.move_line_ids:
                    ml.quantity = demand_qty

        # Validate the transfer and skip the backorder wizard
        picking.with_context(
            immediate_transfer=True,
            skip_sms=True,
            skip_backorder=True,
            picking_ids_not_to_backorder=picking.ids,
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
                payment = self.env['account.payment'].create({
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': invoice.partner_id.id,
                    'amount': invoice.amount_residual,
                    'journal_id': payment_journal.id,
                    'date': fields.Date.today(),
                    'memo': invoice.name,
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
    # CANCEL ORDER
    # =========================================================

    def action_cancel(self):
        for order in self:
            if order.quick_sale_type != 'quick_sale':
                continue

            if order._is_enabled('auto_return_delivery_on_cancel'):
                for picking in order.picking_ids.filtered(
                    lambda p: p.state == 'done'
                ):
                    try:
                        return_wizard = self.env[
                            'stock.return.picking'
                        ].with_context(
                            active_id=picking.id,
                            active_ids=[picking.id],
                            active_model='stock.picking',
                        ).create({})

                        result = return_wizard.action_create_returns()
                        return_picking = self.env['stock.picking'].browse(
                            result.get('res_id')
                        )

                        if return_picking.state in (
                            'confirmed', 'waiting', 'assigned'
                        ):
                            return_picking.action_assign()

                        for move in return_picking.move_ids:
                            if not move.move_line_ids:
                                self.env['stock.move.line'].create({
                                    'move_id': move.id,
                                    'picking_id': return_picking.id,
                                    'product_id': move.product_id.id,
                                    'product_uom_id': move.product_uom.id,
                                    'location_id': move.location_id.id,
                                    'location_dest_id': move.location_dest_id.id,
                                    'quantity': move.product_uom_qty,
                                })
                            else:
                                for ml in move.move_line_ids:
                                    ml.quantity = move.product_uom_qty

                        return_picking.button_validate()
                        order.message_post(
                            body=_('Return Delivery created automatically.')
                        )

                    except Exception as e:
                        _logger.error('RETURN PICKING ERROR: %s', str(e))

            if order._is_enabled('auto_cancel_invoice_on_cancel'):
                for invoice in order.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted'
                ):
                    try:
                        for line in invoice.line_ids.filtered(
                            lambda l:
                            l.account_id.account_type == 'asset_receivable'
                        ):
                            if line.reconciled:
                                line.remove_move_reconcile()

                        invoice.button_draft()
                        invoice.button_cancel()
                        order.message_post(
                            body=_('Invoice %s cancelled automatically.') % invoice.name
                        )

                    except Exception as e:
                        _logger.error('INVOICE CANCEL ERROR: %s', str(e))

            for picking in order.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel')
            ):
                try:
                    picking.action_cancel()
                except Exception as e:
                    _logger.error('PICKING CANCEL ERROR: %s', str(e))

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