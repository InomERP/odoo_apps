# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Kept in sync with sale_order_merge_wizard.MERGEABLE_STATES.
MERGEABLE_STATES = ('draft', 'sent')


class SaleOrderMergeSameCustomerWizard(models.TransientModel):
    """Phase 4: a dedicated entry point (Sales > Orders > Merge Sale for Same
    Customer) that lets the user pick a customer first. All of that customer's
    draft/sent orders are then auto-loaded into an editable list, so the user
    doesn't have to go select them one by one from the list view.

    The actual merge is delegated to `sale.order.merge.wizard` (Phase 1-3) so
    that the tested merge logic is reused as-is and never duplicated.
    """
    _name = 'sale.order.merge.same.customer.wizard'
    _description = 'Merge Sale Orders for Same Customer Wizard'

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        help="Pick a customer to automatically load all of their draft/sent quotations below.",
    )
    order_ids = fields.Many2many(
        'sale.order',
        string='Orders to Merge',
        domain="[('partner_id', '=', customer_id), ('state', 'in', ('draft', 'sent'))]",
        help="Auto-loaded when a customer is chosen. Remove any order you don't want "
             "to include before merging.",
    )
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
    )
    merge_with_order_id = fields.Many2one(
        'sale.order',
        string='Merge With',
        domain="[('id', 'in', order_ids)]",
        help="Existing order (from the list below) that will receive the other orders' lines. "
             "Only used for the 'Merge order on existing selected order' merge types.",
    )

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """Auto-load the customer's draft/sent orders as soon as they are picked."""
        if self.customer_id:
            self.order_ids = self.env['sale.order'].search([
                ('partner_id', '=', self.customer_id.id),
                ('state', 'in', MERGEABLE_STATES),
            ])
        else:
            self.order_ids = [(5, 0, 0)]
        # The customer changed, so any previously chosen merge target is no
        # longer guaranteed to be part of the (new) order list.
        self.merge_with_order_id = False

    def action_merge(self):
        """Delegate the actual merge to the Phase 1-3 wizard, unchanged."""
        self.ensure_one()
        if not self.customer_id:
            raise UserError(_("Please choose a customer first."))
        if len(self.order_ids) < 2:
            raise UserError(_(
                "Please keep at least two orders in the list to merge."
            ))

        core_wizard = self.env['sale.order.merge.wizard'].with_context(
            active_ids=self.order_ids.ids,
        ).create({
            'merge_type': self.merge_type,
            'merge_with_order_id': self.merge_with_order_id.id
            if self.merge_with_order_id else False,
        })
        return core_wizard.action_merge()
