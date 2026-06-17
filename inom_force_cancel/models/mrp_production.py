# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    inom_can_force_cancel = fields.Boolean(
        string="Force Cancel Available",
        compute='_compute_inom_can_force_cancel',
        help="Technical field used to show the Force Cancel button only to "
             "users that are allowed to force cancel orders.",
    )

    def _compute_inom_can_force_cancel(self):
        allowed = self.env.user.sudo().inom_mo_force_cancel_allowed
        for production in self:
            production.inom_can_force_cancel = allowed

    def _inom_check_force_cancel_rights(self):
        """Make sure the current user is allowed to force cancel manufacturing
        orders."""
        if not self.env.user.sudo().inom_mo_force_cancel_allowed:
            raise UserError(_(
                "You are not allowed to force cancel manufacturing orders. Ask "
                "an administrator to enable 'Allow Manufacturing Order "
                "Cancellation' on your user record."))

    def action_inom_force_cancel(self):
        """Force cancel a manufacturing order even when it is already done.

        The component and finished-product stock is reverted, the related
        stock moves and work orders are cancelled, and the order status falls
        back to 'Cancelled' (the status is computed from the finished moves,
        so cancelling every finished move cancels the order).
        """
        self._inom_check_force_cancel_rights()
        for production in self:
            moves = production.move_raw_ids | production.move_finished_ids

            done_moves = moves.filtered(lambda m: m.state == 'done')
            if done_moves:
                done_moves._inom_revert_done_quantities()
                done_moves.write({'state': 'cancel'})

            pending_moves = moves.filtered(
                lambda m: m.state not in ('done', 'cancel'))
            if pending_moves:
                pending_moves.with_context(skip_mo_check=True)._action_cancel()

            work_orders = production.workorder_ids.filtered(
                lambda wo: wo.state != 'cancel')
            if work_orders:
                work_orders.action_cancel()

            production.message_post(body=_(
                "Manufacturing order force cancelled: the stock moves and work "
                "orders have been cancelled and the produced quantity has been "
                "reverted."))
        return True