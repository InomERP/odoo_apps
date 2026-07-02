# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class PurchaseReceiptBillWizard(models.TransientModel):
    _name = 'purchase.receipt.bill.wizard'
    _description = 'Create Vendor Bill from Receipts'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
    )
    purchase_order_ids = fields.Many2many(
        comodel_name='purchase.order',
        string='Purchase Orders',
    )
    line_ids = fields.One2many(
        comodel_name='purchase.receipt.bill.wizard.line',
        inverse_name='wizard_id',
        string='Receipt Lines',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        if context.get('active_model') != 'purchase.order':
            return res
        orders = self.env['purchase.order'].browse(
            context.get('active_ids', [])).exists()
        if not orders:
            return res

        vendors = orders.mapped('partner_id')
        if len(vendors) > 1:
            raise UserError(_(
                'The selected purchase orders must belong to the same vendor.'))
        currencies = orders.mapped('currency_id')
        if len(currencies) > 1:
            raise UserError(_(
                'The selected purchase orders must share the same currency.'))
        companies = orders.mapped('company_id')
        if len(companies) > 1:
            raise UserError(_(
                'The selected purchase orders must belong to the same company.'))

        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        line_commands = []
        for move in orders._get_billable_receipt_moves(precision):
            pol = move.purchase_line_id
            remaining = move.quantity - move.qty_billed
            line_commands.append((0, 0, {
                'move_id': move.id,
                'picking_id': move.picking_id.id,
                'purchase_line_id': pol.id,
                'product_id': move.product_id.id,
                'product_uom_id': pol.product_uom.id,
                'qty_received': move.quantity,
                'qty_billed_already': move.qty_billed,
                'qty_remaining': remaining,
                'qty_to_bill': remaining,
                'price_unit': pol.price_unit,
                'tax_ids': [(6, 0, pol.taxes_id.ids)],
                'selected': True,
            }))

        res.update({
            'partner_id': vendors.id,
            'company_id': companies.id,
            'currency_id': currencies.id,
            'purchase_order_ids': [(6, 0, orders.ids)],
            'line_ids': line_commands,
        })
        return res

    def _get_source_orders(self):
        """Resolve source orders reliably: prefer the stored field, fall back
        to the launching context (which always round-trips)."""
        orders = self.purchase_order_ids
        if not orders and self.env.context.get('active_model') == \
                'purchase.order':
            orders = self.env['purchase.order'].browse(
                self.env.context.get('active_ids', [])).exists()
        return orders

    def _collect_user_inputs(self, moves):
        """Build {move_id: (selected, qty_to_bill)} from the wizard lines.

        Editable inputs (selected, qty_to_bill) round-trip reliably; the
        read-only source fields may not, so lines are matched to the
        server-derived moves either by their move reference (when present) or
        by position, which follows the same deterministic order as default_get.
        """
        inputs = {}
        lines = self.line_ids
        if lines and all(line.move_id for line in lines):
            for line in lines:
                inputs[line.move_id.id] = (line.selected, line.qty_to_bill)
        elif len(lines) == len(moves):
            for line, move in zip(lines, moves):
                inputs[move.id] = (line.selected, line.qty_to_bill)
        return inputs

    def action_create_bill(self):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')

        orders = self._get_source_orders()
        if not orders:
            raise UserError(_('No source purchase order could be resolved.'))

        moves = orders._get_billable_receipt_moves(precision)
        if not moves:
            raise UserError(_(
                'There is no validated receipt left to bill for the selected '
                'purchase order(s).'))

        inputs = self._collect_user_inputs(moves)

        partner = orders.mapped('partner_id')
        company = orders.mapped('company_id')
        currency = orders.mapped('currency_id')

        invoice_line_vals = []
        billed_items = []
        for move in moves:
            selected, qty_to_bill = inputs.get(move.id, (True, None))
            if not selected:
                continue
            remaining = move.quantity - move.qty_billed
            if qty_to_bill is None or float_compare(
                    qty_to_bill, 0.0, precision_digits=precision) <= 0:
                bill_qty = remaining
            else:
                bill_qty = min(qty_to_bill, remaining)
            if float_compare(bill_qty, 0.0, precision_digits=precision) <= 0:
                continue
            pol = move.purchase_line_id
            invoice_line_vals.append((0, 0, {
                'product_id': move.product_id.id,
                'name': pol.name or move.product_id.display_name,
                'quantity': bill_qty,
                'product_uom_id': pol.product_uom.id,
                'price_unit': pol.price_unit,
                'tax_ids': [(6, 0, pol.taxes_id.ids)],
                'purchase_line_id': pol.id,
                'receipt_move_id': move.id,
            }))
            billed_items.append(
                (pol.order_id, move.product_id, bill_qty, pol.product_uom))

        if not invoice_line_vals:
            raise UserError(_(
                'Please select at least one receipt line with a quantity to '
                'bill.'))

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'company_id': company.id,
            'currency_id': currency.id,
            'invoice_origin': ', '.join(orders.mapped('name')),
            'invoice_line_ids': invoice_line_vals,
        })

        self._log_bill_creation(bill, billed_items)

        return {
            'name': _('Vendor Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _log_bill_creation(self, bill, billed_items):
        """Log a note in the chatter of each source purchase order, listing the
        quantities that were billed and linking to the created vendor bill."""
        bill_link = bill._get_html_link() if hasattr(
            bill, '_get_html_link') else Markup('%s') % bill.display_name
        by_order = {}
        for order, product, qty, uom in billed_items:
            by_order.setdefault(order, []).append((product, qty, uom))
        for order, items in by_order.items():
            rows = Markup('').join(
                Markup('<li>%s: %s %s</li>') % (
                    product.display_name, qty, uom.name or '')
                for product, qty, uom in items
            )
            body = Markup(_(
                'Draft vendor bill %(bill)s created from receipts:'
            )) % {'bill': bill_link}
            body = body + Markup('<ul>%s</ul>') % rows
            order.message_post(body=body)


class PurchaseReceiptBillWizardLine(models.TransientModel):
    _name = 'purchase.receipt.bill.wizard.line'
    _description = 'Receipt Line to Bill'

    wizard_id = fields.Many2one(
        comodel_name='purchase.receipt.bill.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    selected = fields.Boolean(string='Bill', default=True)
    move_id = fields.Many2one(
        comodel_name='stock.move',
        string='Receipt Move',
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Receipt',
    )
    purchase_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        string='Purchase Order Line',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit',
    )
    qty_received = fields.Float(
        string='Received',
        digits='Product Unit of Measure',
    )
    qty_billed_already = fields.Float(
        string='Already Billed',
        digits='Product Unit of Measure',
    )
    qty_remaining = fields.Float(
        string='Remaining',
        digits='Product Unit of Measure',
    )
    qty_to_bill = fields.Float(
        string='Qty to Bill',
        digits='Product Unit of Measure',
    )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price',
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
    )

    @api.onchange('selected')
    def _onchange_selected(self):
        for line in self:
            if not line.selected:
                line.qty_to_bill = 0.0
            elif float_is_zero(
                line.qty_to_bill,
                precision_rounding=line.product_uom_id.rounding or 0.01,
            ):
                line.qty_to_bill = line.qty_remaining
