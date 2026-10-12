# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    credit_state = fields.Selection(
        selection=[
            ('none', 'Not Controlled'),
            ('ok', 'Within Limit'),
            ('warn', 'Near / Over Limit (Warning)'),
            ('blocked', 'Over Limit (Blocked)'),
            ('hold', 'Customer On Hold'),
            ('approved', 'Override Approved'),
        ],
        string="Credit Status",
        compute='_compute_credit_state')
    credit_available_display = fields.Monetary(
        string="Available Credit",
        compute='_compute_credit_state',
        currency_field='company_currency_id')
    company_currency_id = fields.Many2one(
        related='company_id.currency_id', string="Company Currency",
        ondelete='set null')
    credit_override = fields.Boolean(
        string="Credit Override", copy=False, tracking=True,
        help="Set by a credit manager to allow confirmation despite "
             "the credit limit.")
    credit_override_reason = fields.Char(
        string="Override Reason", copy=False)
    credit_approval_requested = fields.Boolean(
        string="Credit Approval Requested", copy=False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _inom_order_amount_company(self):
        """Order total expressed in company currency."""
        self.ensure_one()
        amount = self.amount_total
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            amount = self.currency_id._convert(
                amount, self.company_id.currency_id, self.company_id,
                self.date_order or fields.Date.context_today(self))
        return amount

    def _inom_credit_evaluate(self):
        """Evaluate this order against the customer's credit position."""
        self.ensure_one()
        if not self.partner_id:
            return {'enabled': False}
        extra = 0.0
        if self.state in ('draft', 'sent'):
            # A draft order is not yet part of the exposure.
            extra = self._inom_order_amount_company()
        result = self.partner_id._smart_credit_evaluate(extra_amount=extra)
        return result

    # ------------------------------------------------------------------
    # Computes / onchange
    # ------------------------------------------------------------------
    @api.depends('partner_id', 'amount_total', 'state',
                 'credit_override', 'order_line')
    def _compute_credit_state(self):
        checkpoint = self.env['res.partner']._inom_get_param(
            'checkpoint_so', 'block')
        for order in self:
            result = order._inom_credit_evaluate()
            if not result.get('enabled'):
                order.credit_state = 'none'
                order.credit_available_display = 0.0
                continue
            order.credit_available_display = result['available']
            if order.credit_override:
                order.credit_state = 'approved'
            elif result['hold']:
                order.credit_state = 'hold'
            elif result['exceeded']:
                action = result['partner']._inom_resolve_action(checkpoint)
                if action == 'block':
                    order.credit_state = 'blocked'
                elif action == 'warn':
                    order.credit_state = 'warn'
                else:
                    order.credit_state = 'ok'
            else:
                order.credit_state = 'ok'

    @api.onchange('partner_id')
    def _onchange_partner_id_smart_credit(self):
        if not self.partner_id:
            return
        effective = self.partner_id._smart_credit_effective_partner()
        if not effective:
            return
        if effective.is_credit_hold:
            return {'warning': {
                'title': _("Customer on credit hold"),
                'message': _(
                    "%(partner)s is currently on credit hold "
                    "(%(reason)s). Sale confirmations are blocked until "
                    "the hold is released.",
                    partner=effective.name,
                    reason=effective.credit_hold_reason or _("no reason")),
            }}
        if effective.smart_available_credit <= 0:
            return {'warning': {
                'title': _("Credit limit reached"),
                'message': _(
                    "%(partner)s has no available credit left "
                    "(exposure %(exposure).2f / limit %(limit).2f).",
                    partner=effective.name,
                    exposure=effective.smart_credit_exposure,
                    limit=effective.smart_credit_limit
                    + effective.smart_extra_credit),
            }}

    # ------------------------------------------------------------------
    # Confirmation gate
    # ------------------------------------------------------------------
    def action_confirm(self):
        Audit = self.env['inom.credit.audit']
        checkpoint = self.env['res.partner']._inom_get_param(
            'checkpoint_so', 'block')
        for order in self:
            result = order._inom_credit_evaluate()
            if not result.get('enabled') or order.credit_override:
                continue
            partner = result['partner']
            if result['hold']:
                Audit._log(partner, 'block',
                           amount=order._inom_order_amount_company(),
                           note=_("Confirmation stopped: customer on "
                                  "credit hold."),
                           document=order)
                return order._inom_open_credit_wizard(result, hold=True)
            if result['exceeded']:
                action = partner._inom_resolve_action(checkpoint)
                if action == 'block':
                    Audit._log(partner, 'block',
                               amount=result['over_amount'],
                               note=_("Confirmation blocked: credit limit "
                                      "exceeded."),
                               document=order)
                    return order._inom_open_credit_wizard(result)
                if action == 'warn':
                    Audit._log(partner, 'warn',
                               amount=result['over_amount'],
                               note=_("Confirmed with credit warning."),
                               document=order)
                    order.message_post(body=_(
                        "Credit warning: this order exceeds the "
                        "customer's smart credit limit by %(amount).2f "
                        "(policy: warn only).",
                        amount=result['over_amount']))
        return super().action_confirm()

    def _inom_open_credit_wizard(self, result, hold=False):
        self.ensure_one()
        partner = result['partner']
        wizard = self.env['inom.credit.check.wizard'].create({
            'order_id': self.id,
            'partner_id': partner.id,
            'is_hold': hold,
            'hold_reason': partner.credit_hold_reason or '',
            'credit_limit': partner.smart_credit_limit,
            'extra_credit': partner.smart_extra_credit,
            'credit_exposure': partner.smart_credit_exposure,
            'available_credit': result['available'],
            'order_amount': self._inom_order_amount_company(),
            'over_amount': result['over_amount'],
            'credit_score': partner.smart_credit_score,
        })
        return {
            'name': _("Smart Credit Check"),
            'type': 'ir.actions.act_window',
            'res_model': 'inom.credit.check.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_credit_wizard(self):
        """Header button for credit managers on blocked / held orders."""
        self.ensure_one()
        result = self._inom_credit_evaluate()
        if not result.get('enabled'):
            return True
        return self._inom_open_credit_wizard(
            result, hold=result.get('hold', False))
