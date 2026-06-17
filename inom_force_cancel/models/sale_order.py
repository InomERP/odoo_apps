# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    inom_can_force_cancel = fields.Boolean(
        string="Force Cancel Available",
        compute='_compute_inom_can_force_cancel',
        help="Technical field used to show the Force Cancel button only to "
             "users that are allowed to force cancel orders.",
    )

    def _compute_inom_can_force_cancel(self):
        allowed = self.env.user.sudo().inom_so_force_cancel_allowed
        for order in self:
            order.inom_can_force_cancel = allowed

    def _inom_check_force_cancel_rights(self):
        """Make sure the current user is allowed to force cancel sale orders."""
        if not self.env.user.sudo().inom_so_force_cancel_allowed:
            raise UserError(_(
                "You are not allowed to force cancel sale orders. Ask an "
                "administrator to enable 'Allow Sale Order Cancellation' on "
                "your user record."))

    def action_inom_force_cancel(self):
        """Force cancel a confirmed / delivered sale order together with its
        deliveries and invoices, restoring the delivered stock."""
        self._inom_check_force_cancel_rights()
        for order in self:
            order.invoice_ids._inom_force_cancel()
            order.picking_ids._inom_force_cancel()
            if order.state != 'cancel':
                order.write({'state': 'cancel'})
            order.message_post(body=_(
                "Order force cancelled: the related deliveries and invoices "
                "have been cancelled and the delivered stock has been "
                "restored."))
        return True