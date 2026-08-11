# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _inom_credit_controlled_pickings(self):
        """Outgoing transfers the delivery checkpoint applies to."""
        return self.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.partner_id)

    def _inom_check_credit(self, checkpoint):
        """Apply the delivery checkpoint to a single transfer.

        Raises when the transfer must be stopped. Returns the data needed
        to record a warning, or ``None`` when nothing has to be logged.
        """
        self.ensure_one()
        result = self.partner_id._smart_credit_evaluate()
        if not result.get('enabled'):
            return None
        partner = result['partner']
        if result['hold']:
            raise UserError(_(
                "Delivery %(picking)s cannot be validated: customer "
                "%(partner)s is on credit hold (%(reason)s).",
                picking=self.name, partner=partner.name,
                reason=partner.credit_hold_reason or _("no reason")))
        # The exposure already includes the confirmed order behind this
        # delivery, so the gate is simply: is the customer over the limit?
        if result['available'] >= 0:
            return None
        action = partner._inom_resolve_action(checkpoint)
        if action == 'block':
            raise UserError(_(
                "Delivery %(picking)s cannot be validated: customer "
                "%(partner)s is over the smart credit limit by "
                "%(amount).2f. Register a payment or adjust the limit "
                "first.",
                picking=self.name, partner=partner.name,
                amount=-result['available']))
        if action == 'warn':
            return partner, -result['available']
        return None

    def _inom_log_credit_warning(self, partner, over_amount):
        """Record that a transfer went out while over the limit."""
        self.ensure_one()
        self.env['inom.credit.audit']._log(
            partner, 'warn', amount=over_amount,
            note=_("Delivery validated while over the credit limit."),
            document=self)
        self.message_post(body=_(
            "Credit warning: customer is over the smart credit limit by "
            "%(amount).2f.", amount=over_amount))

    def button_validate(self):
        checkpoint = self.env['res.partner']._inom_get_param(
            'checkpoint_delivery', 'warn')
        pending_warnings = {}
        if checkpoint != 'off':
            for picking in self._inom_credit_controlled_pickings():
                warning = picking._inom_check_credit(checkpoint)
                if warning:
                    pending_warnings[picking.id] = warning

        res = super().button_validate()

        # button_validate may return an intermediate wizard (SMS, backorder,
        # immediate transfer) and then be called again for the same picking.
        # Record the warning only once, when the transfer is really done.
        for picking in self.browse(list(pending_warnings)):
            if picking.state == 'done':
                picking._inom_log_credit_warning(
                    *pending_warnings[picking.id])
        return res
