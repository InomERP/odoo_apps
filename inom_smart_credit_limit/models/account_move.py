# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _inom_credit_controlled_moves(self):
        """Direct customer invoices the credit checkpoint applies to.

        Invoices generated from a sale order are excluded: their amount is
        already part of the order exposure, so gating them again would
        double count the same commitment.
        """
        return self.filtered(
            lambda m: m.move_type == 'out_invoice' and m.partner_id
            and not any(m.invoice_line_ids.mapped('sale_line_ids')))

    def _inom_invoice_amount_company(self):
        """Invoice total expressed in the company currency."""
        self.ensure_one()
        amount = self.amount_total
        if self.currency_id and \
                self.currency_id != self.company_id.currency_id:
            amount = self.currency_id._convert(
                amount, self.company_id.currency_id, self.company_id,
                self.invoice_date or self.date)
        return amount

    def _inom_check_credit(self, checkpoint):
        """Apply the invoice checkpoint to a single invoice."""
        self.ensure_one()
        result = self.partner_id._smart_credit_evaluate(
            extra_amount=self._inom_invoice_amount_company())
        if not result.get('enabled'):
            return
        if not (result['hold'] or result['exceeded']):
            return
        partner = result['partner']
        action = partner._inom_resolve_action(checkpoint)
        if result['hold'] or action == 'block':
            raise UserError(_(
                "Invoice %(move)s cannot be posted: customer %(partner)s "
                "is %(state)s.",
                move=self.display_name, partner=partner.name,
                state=_("on credit hold") if result['hold']
                else _("over the smart credit limit")))
        if action == 'warn':
            self.env['inom.credit.audit']._log(
                partner, 'warn', amount=result['over_amount'],
                note=_("Invoice posted while over the credit limit."),
                document=self)
            self.message_post(body=_(
                "Credit warning: posting this invoice takes the customer "
                "over the smart credit limit by %(amount).2f.",
                amount=result['over_amount']))

    def _post(self, soft=True):
        checkpoint = self.env['res.partner']._inom_get_param(
            'checkpoint_invoice', 'off')
        if checkpoint != 'off':
            for move in self._inom_credit_controlled_moves():
                move._inom_check_credit(checkpoint)
        return super()._post(soft=soft)
