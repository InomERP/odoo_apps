# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sales_view_type = fields.Selection(
        [
            ('regular', 'Regular'),
            ('instant_sale', 'Instant Sale'),
        ],
        string='Sales View Type',
        default='regular',
        copy=False,
        tracking=True
    )

    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain=[('usage', '=', 'internal')],
        copy=False,
    )

    # =========================================================
    # CONFIG
    # =========================================================

    def _get_config(self, key, default='False'):

        return self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'mst_instant_sale.%s' % key,
            default=default
        )

    def _is_enabled(self, key):

        val = self._get_config(key)

        return str(val).lower() in (
            'true',
            '1'
        )

    # =========================================================
    # CREATE ORDER WITH CUSTOM SEQUENCE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get('sales_view_type') == 'instant_sale':

                vals['name'] = self.env[
                    'ir.sequence'
                ].next_by_code(
                    'instant.sale.order'
                ) or _('New')

        return super().create(vals_list)

    # =========================================================
    # CONFIRM ORDER
    # =========================================================

    def action_confirm(self):

        for order in self:

            if order.sales_view_type == 'instant_sale':

                allow_negative_stock = order.env[
                    'ir.config_parameter'
                ].sudo().get_param(
                    'mst_instant_sale.allow_negative_stock'
                )

                if str(allow_negative_stock).lower() not in (
                    'true',
                    '1'
                ):

                    for line in order.order_line:

                        product = line.product_id

                        if not product:
                            continue

                        if product.type == 'service':
                            continue

                        available_qty = product.free_qty

                        _logger.warning(
                            'FINAL STOCK CHECK => %s | AVAILABLE => %s | REQUIRED => %s',
                            product.display_name,
                            available_qty,
                            line.product_uom_qty
                        )

                        if available_qty <= 0:

                            raise ValidationError(_(
                                "No stock available for product:\n\n%s"
                            ) % (
                                product.display_name
                            ))

                        if available_qty < line.product_uom_qty:

                            raise ValidationError(_(
                                "Not enough stock for product:\n\n"
                                "%s\n\n"
                                "Available Quantity: %.2f\n"
                                "Required Quantity: %.2f"
                            ) % (
                                product.display_name,
                                available_qty,
                                line.product_uom_qty
                            ))

        result = super().action_confirm()

        for order in self:

            if order.sales_view_type == 'instant_sale':

                order._instant_sale_post_confirm()

        return result

    # =========================================================
    # POST CONFIRM
    # =========================================================

    def _instant_sale_post_confirm(self):

        self.ensure_one()

        if self.source_location_id:

            for picking in self.picking_ids.filtered(
                lambda p:
                p.picking_type_code == 'outgoing'
                and p.state not in (
                    'done',
                    'cancel'
                )
            ):

                picking.location_id = (
                    self.source_location_id
                )

                picking.move_ids.write({
                    'location_id':
                    self.source_location_id.id
                })

        if self._is_enabled(
            'auto_validate_delivery'
        ):

            self._instant_sale_validate_delivery()

        if self._is_enabled(
            'auto_create_invoice'
        ):

            self._instant_sale_create_invoice(
                auto_post=self._is_enabled(
                    'auto_post_invoice'
                )
            )

    # =========================================================
    # VALIDATE PICKING
    # =========================================================

    def _do_validate_picking(
        self,
        picking,
        source_loc_id=False
    ):

        allow_negative = self._is_enabled(
            'allow_negative_stock'
        )

        if source_loc_id:

            picking.write({
                'location_id': source_loc_id
            })

            picking.move_ids.write({
                'location_id': source_loc_id
            })

        if not allow_negative:

            if picking.state in (
                'confirmed',
                'waiting',
                'partially_available'
            ):

                picking.action_assign()

        for move in picking.move_ids.filtered(
            lambda m:
            m.state not in (
                'done',
                'cancel'
            )
        ):

            demand_qty = move.product_uom_qty

            available_qty = move.product_id.free_qty

            if (
                not allow_negative
                and available_qty < demand_qty
            ):

                raise ValidationError(_(
                    "Not enough stock for:\n\n"
                    "%s\n\n"
                    "Available: %.2f\n"
                    "Required: %.2f"
                ) % (
                    move.product_id.display_name,
                    available_qty,
                    demand_qty
                ))

            if not move.move_line_ids:

                self.env[
                    'stock.move.line'
                ].create({
                    'move_id': move.id,
                    'picking_id': picking.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': (
                        source_loc_id
                        or move.location_id.id
                    ),
                    'location_dest_id': (
                        move.location_dest_id.id
                    ),
                    'quantity': demand_qty,
                })

            else:

                for ml in move.move_line_ids:

                    ml.quantity = demand_qty

        picking.button_validate()

    # =========================================================
    # AUTO VALIDATE DELIVERY
    # =========================================================

    def _instant_sale_validate_delivery(self):

        self.ensure_one()

        source_loc_id = (
            self.source_location_id.id
            if self.source_location_id
            else False
        )

        for picking in self.picking_ids.filtered(
            lambda p:
            p.picking_type_code == 'outgoing'
            and p.state not in (
                'done',
                'cancel'
            )
        ):

            self._do_validate_picking(
                picking,
                source_loc_id
            )

    # =========================================================
    # AUTO REGISTER PAYMENT
    # =========================================================

    def _instant_sale_register_payment(
        self,
        invoices
    ):

        self.ensure_one()

        payment_journal = self.env[
            'account.journal'
        ].search([
            ('type', 'in', ['bank', 'cash']),
            (
                'company_id',
                '=',
                self.company_id.id
            ),
        ], limit=1)

        if not payment_journal:
            return

        for invoice in invoices.filtered(
            lambda inv:
            inv.state == 'posted'
            and inv.amount_residual > 0
        ):

            try:

                payment = self.env[
                    'account.payment'
                ].create({
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
                    payment.move_id.line_ids
                    + invoice.line_ids
                ).filtered(
                    lambda line:
                    line.account_id.account_type
                    == 'asset_receivable'
                    and not line.reconciled
                )

                receivable_lines.reconcile()

            except Exception as e:

                _logger.error(
                    'INSTANT SALE PAYMENT ERROR: %s',
                    str(e)
                )

    # =========================================================
    # CREATE INVOICE
    # =========================================================

    def _instant_sale_create_invoice(
        self,
        auto_post=True
    ):

        self.ensure_one()

        invoices = self.env[
            'account.move'
        ]

        if self.invoice_status == 'to invoice':

            invoices = self._create_invoices()

            if auto_post:

                for inv in invoices:

                    if inv.state == 'draft':

                        inv.action_post()

            if self._is_enabled(
                'auto_register_payment'
            ):

                self._instant_sale_register_payment(
                    invoices
                )

        return invoices

    # =========================================================
    # CANCEL ORDER
    # =========================================================

    def action_cancel(self):

        for order in self:

            if order._is_enabled(
                'auto_return_delivery_on_cancel'
            ):

                done_pickings = order.picking_ids.filtered(
                    lambda p:
                    p.state == 'done'
                )

                for picking in done_pickings:

                    try:

                        return_wizard = self.env[
                            'stock.return.picking'
                        ].with_context(
                            active_id=picking.id,
                            active_ids=[picking.id],
                            active_model='stock.picking'
                        ).create({})

                        result = return_wizard.create_returns()

                        return_picking = self.env[
                            'stock.picking'
                        ].browse(
                            result.get('res_id')
                        )

                        if return_picking.state in (
                            'confirmed',
                            'waiting',
                            'assigned'
                        ):

                            return_picking.action_assign()

                        for move in return_picking.move_ids:

                            if not move.move_line_ids:

                                self.env[
                                    'stock.move.line'
                                ].create({
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

                                    ml.quantity = (
                                        move.product_uom_qty
                                    )

                        return_picking.button_validate()

                        order.message_post(
                            body=_(
                                'Return Delivery created automatically.'
                            )
                        )

                    except Exception as e:

                        _logger.error(
                            'RETURN PICKING ERROR: %s',
                            str(e)
                        )

            if order._is_enabled(
                'auto_cancel_invoice_on_cancel'
            ):

                for invoice in order.invoice_ids.filtered(
                    lambda inv:
                    inv.state == 'posted'
                ):

                    try:

                        for line in invoice.line_ids.filtered(
                            lambda l:
                            l.account_id.account_type
                            == 'asset_receivable'
                        ):

                            if line.reconciled:
                                line.remove_move_reconcile()

                        invoice.button_draft()

                        invoice.button_cancel()

                        order.message_post(
                            body=_(
                                'Invoice %s cancelled automatically.'
                            ) % invoice.name
                        )

                    except Exception as e:

                        _logger.error(
                            'INVOICE CANCEL ERROR: %s',
                            str(e)
                        )

            for picking in order.picking_ids.filtered(
                lambda p:
                p.state not in (
                    'done',
                    'cancel'
                )
            ):

                try:

                    picking.action_cancel()

                except Exception as e:

                    _logger.error(
                        'PICKING CANCEL ERROR: %s',
                        str(e)
                    )

        return super().action_cancel()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    instant_sale_order_id = fields.Many2one(
        'sale.order',
        string='Instant Sale Order',
        compute='_compute_instant_sale_order_id',
        store=True,
    )

    @api.depends(
        'sale_id',
        'sale_id.sales_view_type'
    )
    def _compute_instant_sale_order_id(self):

        for picking in self:

            if (
                picking.sale_id
                and picking.sale_id.sales_view_type
                == 'instant_sale'
            ):

                picking.instant_sale_order_id = (
                    picking.sale_id
                )

            else:

                picking.instant_sale_order_id = False