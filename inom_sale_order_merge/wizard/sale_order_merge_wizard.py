# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# States that are allowed to be merged. Confirmed ('sale') and locked ('done')
# quotations must never be merged.
MERGEABLE_STATES = ('draft', 'sent')


class SaleOrderMergeWizard(models.TransientModel):
    _name = 'sale.order.merge.wizard'
    _description = 'Sale Order Merge Wizard'

    merge_type = fields.Selection(
        selection=[
            ('new_cancel', 'New Order and Cancel Selected'),
            ('new_delete', 'New Order and Delete All Selected Order'),
            ('existing_cancel', 'Merge order on existing selected order and cancel others'),
            ('existing_delete', 'Merge order on existing selected order and delete others'),
        ],
        string='Merge Type',
        default='new_cancel',
        required=True,
        help="Choose how the selected orders should be merged:\n"
             "- New Order and Cancel Selected: create a new order and cancel the source orders.\n"
             "- New Order and Delete All Selected Order: create a new order and delete the source orders.\n"
             "- Merge order on existing selected order and cancel others: add the lines of the other "
             "selected orders into the chosen existing order, then cancel the rest.\n"
             "- Merge order on existing selected order and delete others: add the lines of the other "
             "selected orders into the chosen existing order, then delete the rest.",
    )
    merge_with_order_id = fields.Many2one(
        'sale.order',
        string='Merge With',
        domain="[('id', 'in', selected_order_ids)]",
        help="Existing order (from the current selection) that will receive the other orders' lines. "
             "Only used for the 'Merge order on existing selected order' merge types.",
    )
    merge_with_different_customer = fields.Boolean(
        string='Merge with Different Customer',
        help="Tick this to merge orders that belong to different customers. The newly "
             "created merged order will be assigned to the customer chosen below, and all "
             "the other selected orders will be cancelled or deleted as usual. "
             "Only available for the 'New Order' merge types.",
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        help="Customer to assign to the new merged order when merging orders that belong "
             "to different customers.",
    )
    selected_order_ids = fields.Many2many(
        'sale.order',
        string='Selected Orders',
        compute='_compute_selected_order_ids',
    )

    @api.depends_context('active_ids')
    def _compute_selected_order_ids(self):
        order_ids = self.env.context.get('active_ids', [])
        for wizard in self:
            wizard.selected_order_ids = self.env['sale.order'].browse(order_ids).exists()

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def _get_selected_orders(self):
        """Return the sale orders selected in the list view, with basic guards."""
        order_ids = self.env.context.get('active_ids', [])
        orders = self.env['sale.order'].browse(order_ids).exists()
        if len(orders) < 2:
            raise UserError(_("Please select at least two sale orders to merge."))
        return orders

    def _check_orders(self, orders):
        """Validate that the selected orders can be merged together."""
        # State guard: only draft/sent quotations can be merged.
        invalid = orders.filtered(lambda o: o.state not in MERGEABLE_STATES)
        if invalid:
            raise UserError(_(
                "Only quotations in Draft or Sent state can be merged.\n"
                "The following orders cannot be merged: %s"
            ) % ", ".join(invalid.mapped('name')))

        # Same-customer guard — skipped when the user explicitly opted in to
        # merging orders that belong to different customers (Phase 3).
        if not self.merge_with_different_customer and len(orders.mapped('partner_id')) > 1:
            raise UserError(_(
                "All selected orders must belong to the same customer."
            ))

    def _check_different_customer(self):
        """Validate the target customer for the 'merge with different customer' option."""
        if not self.customer_id:
            raise UserError(_(
                "Please choose a customer for the merged order."
            ))

    def _check_merge_with(self, orders):
        """Validate the target order for the 'merge into existing order' types."""
        if not self.merge_with_order_id:
            raise UserError(_(
                "Please choose an existing order in the 'Merge With' field."
            ))
        if self.merge_with_order_id not in orders:
            raise UserError(_(
                "The 'Merge With' order must be one of the selected orders."
            ))

    # ------------------------------------------------------------------
    # Merge building blocks
    # ------------------------------------------------------------------
    def _prepare_merged_order_vals(self, orders):
        """Header values for the newly created merged order."""
        if self.merge_with_different_customer:
            partner = self.customer_id
        else:
            partner = orders[0].partner_id
        return {
            'partner_id': partner.id,
        }

    def _copy_order_lines(self, orders, new_order):
        """Copy all order lines from the source orders into the new order.

        Lines are copied as-is (no product consolidation in Phase 1), so the
        merged order keeps a full, traceable breakdown of every source line.
        """
        for order in orders:
            for line in order.order_line:
                line.copy({'order_id': new_order.id})

    def _post_source_message(self, new_order, orders):
        """Log on the merged order which source orders it was created from."""
        new_order.message_post(
            body=_("This sale order has been created from: %s")
            % ", ".join(orders.mapped('name'))
        )

    def _finalize_sources(self, orders, other_orders=None):
        """Cancel or delete the leftover source orders according to the chosen merge type.

        For the 'new_*' types, ``orders`` (all selected orders) are finalized.
        For the 'existing_*' types, only ``other_orders`` (selected orders minus the
        target) are finalized — the target order must survive untouched.
        """
        to_finalize = other_orders if other_orders is not None else orders
        if self.merge_type in ('new_cancel', 'existing_cancel'):
            to_finalize._action_cancel()
        elif self.merge_type in ('new_delete', 'existing_delete'):
            to_finalize.unlink()

    def _post_merge_message(self, target_order, other_orders):
        """Log on the target order which other orders were merged into it."""
        target_order.message_post(
            body=_("This sale order has been updated by merging: %s")
            % ", ".join(other_orders.mapped('name'))
        )

    # ------------------------------------------------------------------
    # Main action
    # ------------------------------------------------------------------
    def action_merge(self):
        self.ensure_one()
        orders = self._get_selected_orders()
        self._check_orders(orders)

        if self.merge_type in ('existing_cancel', 'existing_delete'):
            return self._action_merge_into_existing(orders)
        return self._action_merge_into_new(orders)

    def _action_merge_into_new(self, orders):
        """Phase 1 behaviour: create a brand-new order from all selected orders.

        Phase 3 addition: if 'Merge with Different Customer' is ticked, the new
        order is assigned to the chosen customer instead of orders[0].partner_id
        (this is also what allows the same-customer guard to be skipped).
        """
        if self.merge_with_different_customer:
            self._check_different_customer()

        SaleOrder = self.env['sale.order']
        new_order = SaleOrder.create(self._prepare_merged_order_vals(orders))
        self._copy_order_lines(orders, new_order)

        # Capture references before the source orders are cancelled/deleted.
        self._post_source_message(new_order, orders)
        self._finalize_sources(orders)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Merged Sale Order'),
            'res_model': 'sale.order',
            'res_id': new_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _action_merge_into_existing(self, orders):
        
        self._check_merge_with(orders)
        target_order = self.merge_with_order_id
        other_orders = orders - target_order

        self._copy_order_lines(other_orders, target_order)
        self._post_merge_message(target_order, other_orders)
        self._finalize_sources(orders, other_orders=other_orders)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Merged Sale Order'),
            'res_model': 'sale.order',
            'res_id': target_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
