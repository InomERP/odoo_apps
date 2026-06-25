# -*- coding: utf-8 -*-
# Part of inom_mo_reset. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

# Work order states (Odoo 19) that represent a "finished or aborted" operation.
# These are the states we want to revive when an MO is reset to draft.
_WO_INACTIVE_STATES = ('cancel',)
# Target state a revived work order should land in. Odoo 19 work orders do not
# have a "pending" state; the functional "Pending / ready to restart" state maps
# to 'ready' (labelled "To Do" in the UI), which is also the model default.
_WO_RESET_STATE = 'ready'

# Stock move states considered "dead" after a cancellation. Reviving them means
# putting them back to 'draft' so action_confirm() can re-confirm/reserve them.
_MOVE_RESET_STATE = 'draft'


class MrpProduction(models.Model):
    """Extend the Manufacturing Order to allow resetting a *cancelled* order
    back to *Draft* without losing any data.

    Implementation notes
    ---------------------
    ``mrp.production.state`` is a *stored computed* field. Its compute method
    (``_compute_state``) is intentionally "sticky" on the ``cancel`` value:
    once an order is cancelled the compute keeps returning ``cancel`` even if
    the underlying moves change. Therefore reviving the moves/work orders is not
    enough -- we must perform an explicit ``write({'state': 'draft'})`` to lift
    the order out of the cancelled state. This mirrors how core Odoo performs
    out-of-cancel transitions ("some state changes outside of this compute").
    """

    _inherit = 'mrp.production'

    # ------------------------------------------------------------------
    # Fields (F9 - Set to Draft Flag Tracking)
    # ------------------------------------------------------------------
    set_to_draft = fields.Boolean(
        string='Reset to Draft',
        default=False,
        copy=False,
        tracking=True,
        help="Technical flag. Set to True when a cancelled Manufacturing "
             "Order has been reset to Draft and not yet re-confirmed or "
             "re-cancelled. Automatically cleared by confirm / plan / unplan / "
             "cancel. Provides a lightweight audit trail of reset orders.",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _inom_can_set_to_draft(self):
        """Return the recordset of orders that are eligible to be reset.

        Only *cancelled* orders qualify (F2). Used both by the UI helper and as
        a server-side guard so the rule cannot be bypassed via RPC.
        """
        return self.filtered(lambda mo: mo.state == 'cancel')

    def _inom_check_reset_access(self):
        """Defense-in-depth security check (F12 / security).

        The button already carries a ``groups`` restriction in the view, but a
        malicious or scripted RPC call could still reach the method. We re-check
        membership server-side so the access rule is always enforced.

        Mirrors the view's visibility rule: allowed for the System administrator
        OR any user explicitly granted the reset group. A plain Manufacturing
        user/manager is rejected.
        """
        user = self.env.user
        if not (user.has_group('base.group_system')
                or user.has_group('inom_mo_reset.group_mo_reset_user')):
            raise AccessError(_(
                "You are not allowed to reset Manufacturing Orders to draft. "
                "Please contact your administrator."
            ))

    # ------------------------------------------------------------------
    # Main action (F1, F3, F4, F5, F6, F7, F8)
    # ------------------------------------------------------------------
    def action_set_to_draft(self):
        """Reset cancelled Manufacturing Orders back to the *Draft* state.

        Preserves every business field (product, BoM, quantities, dates,
        responsible, notes -- F4/F6/F7), revives raw & finished stock moves to
        ``draft`` (F5) and restores work orders to ``ready`` (F8). Runs
        synchronously with no background job (F13) and is safe for concurrent
        multi-user use (F12) thanks to standard per-row transactional locking.
        """
        self._inom_check_reset_access()

        resettable = self._inom_can_set_to_draft()
        not_cancelled = self - resettable
        if not_cancelled:
            raise UserError(_(
                "Only cancelled Manufacturing Orders can be reset to draft.\n"
                "The following order(s) are not cancelled: %s",
                ", ".join(not_cancelled.mapped('name')),
            ))
        if not resettable:
            return True

        for production in resettable:
            production._inom_revive_moves()
            production._inom_revive_workorders()

        # Lift the orders out of 'cancel'. The state field is stored+computed and
        # sticky on cancel, so a direct write is required (see class docstring).
        # Writing the moves/work orders above does NOT auto-recompute out of
        # cancel; this explicit write does, and the flag is set in the same call.
        resettable.write({
            'state': 'draft',
            'set_to_draft': True,
        })

        # Audit trail in chatter (F9). Done after the state write so the message
        # reflects the new state. Kept lightweight and in English only.
        for production in resettable:
            production.message_post(body=_(
                "Manufacturing Order reset to <b>Draft</b> from <b>Cancelled</b> "
                "state. All data, raw material moves and work orders preserved."
            ))
            _logger.info(
                "MO %s (id=%s) reset to draft by user %s (id=%s)",
                production.name, production.id,
                self.env.user.login, self.env.uid,
            )
        return True

    def _inom_revive_moves(self):
        """Reset the cancelled raw & finished stock moves back to draft (F5).

        Only moves currently in ``cancel`` are touched -- already done moves are
        never resurrected. ``picked`` is cleared so a subsequent confirm behaves
        like a fresh order. Stale move lines from the cancelled run are removed.
        """
        self.ensure_one()
        dead_moves = (self.move_raw_ids | self.move_finished_ids).filtered(
            lambda m: m.state == 'cancel'
        )
        if not dead_moves:
            return
        # Drop any leftover reservation / done lines from the cancelled run.
        stale_lines = dead_moves.move_line_ids
        if stale_lines:
            stale_lines.unlink()
        dead_moves.write({
            'state': _MOVE_RESET_STATE,
            'picked': False,
        })

    def _inom_revive_workorders(self):
        """Restore cancelled work orders to the ``ready`` state (F8).

        Odoo 19 work orders have no 'pending' state; 'ready' ("To Do") is the
        equivalent restart-ready state and the model default. Only work orders
        in ``cancel`` are revived; finished ones are left untouched.
        """
        self.ensure_one()
        dead_workorders = self.workorder_ids.filtered(
            lambda w: w.state in _WO_INACTIVE_STATES
        )
        if dead_workorders:
            # Direct write: WO _compute_state is sticky outside ('blocked',
            # 'ready'), so reviving must be an explicit write.
            dead_workorders.write({'state': _WO_RESET_STATE})

    # ------------------------------------------------------------------
    # Standard Odoo method integration (F10) -- flag lifecycle management
    # ------------------------------------------------------------------
    def action_confirm(self):
        """Clear the reset flag when the order is (re)confirmed (F9/F10)."""
        res = super().action_confirm()
        flagged = self.filtered('set_to_draft')
        if flagged:
            flagged.set_to_draft = False
        return res

    def button_plan(self):
        """Clear the reset flag when planning (which confirms drafts) (F10)."""
        res = super().button_plan()
        flagged = self.filtered('set_to_draft')
        if flagged:
            flagged.set_to_draft = False
        return res

    def button_unplan(self):
        """Keep the reset flag consistent on unplan (F10).

        Unplanning operates on already-confirmed orders, so the flag is normally
        already False; clearing here is idempotent and guards edge cases.
        """
        res = super().button_unplan()
        flagged = self.filtered('set_to_draft')
        if flagged:
            flagged.set_to_draft = False
        return res

    def action_cancel(self):
        """Clear the reset flag when the order is cancelled again (F9/F10)."""
        res = super().action_cancel()
        flagged = self.filtered('set_to_draft')
        if flagged:
            flagged.set_to_draft = False
        return res
