# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class InomCreditCheckWizard(models.TransientModel):
    _name = 'inom.credit.check.wizard'
    _description = 'Smart Credit Check'

    order_id = fields.Many2one(
        'sale.order', string="Sale Order", required=True, readonly=True,
        ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner', string="Customer", readonly=True,
        ondelete='cascade')
    company_id = fields.Many2one(
        'res.company', string="Company", ondelete='cascade',
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string="Currency",
        ondelete='set null')
    is_hold = fields.Boolean(string="Customer On Hold", readonly=True)
    hold_reason = fields.Char(string="Hold Reason", readonly=True)
    credit_limit = fields.Monetary(
        string="Credit Limit", readonly=True,
        currency_field='currency_id')
    extra_credit = fields.Monetary(
        string="Active Extensions", readonly=True,
        currency_field='currency_id')
    credit_exposure = fields.Monetary(
        string="Current Exposure", readonly=True,
        currency_field='currency_id')
    available_credit = fields.Monetary(
        string="Available Credit", readonly=True,
        currency_field='currency_id')
    order_amount = fields.Monetary(
        string="This Order", readonly=True,
        currency_field='currency_id')
    over_amount = fields.Monetary(
        string="Exceeding By", readonly=True,
        currency_field='currency_id')
    credit_score = fields.Integer(string="Credit Score", readonly=True)
    override_reason = fields.Char(
        string="Override Reason",
        help="Mandatory business justification recorded in the credit "
             "audit log.")

    def action_request_approval(self):
        """Notify credit managers and flag the order for review."""
        self.ensure_one()
        order = self.order_id
        Audit = self.env['inom.credit.audit']
        managers = self.env['res.partner']._inom_manager_users()
        note = _(
            "Credit approval requested for %(order)s: order amount "
            "%(amount).2f, available credit %(available).2f, exceeding "
            "by %(over).2f.",
            order=order.name, amount=self.order_amount,
            available=self.available_credit, over=self.over_amount)
        for user in managers:
            order.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_("Credit limit approval requested"),
                note=note,
                user_id=user.id)
        order.message_post(body=note)
        order.credit_approval_requested = True
        Audit._log(self.partner_id, 'approval_request',
                   amount=self.over_amount, note=note, document=order)
        return {'type': 'ir.actions.act_window_close'}

    def action_override_confirm(self):
        """Credit manager override: record the reason and confirm."""
        self.ensure_one()
        if not self.env.user.has_group(
                'inom_smart_credit_limit.group_smart_credit_manager'):
            raise UserError(_(
                "Only a Smart Credit Manager can override a credit "
                "block."))
        if not self.override_reason:
            raise UserError(_(
                "Please provide a business reason for the override."))
        order = self.order_id
        order.write({
            'credit_override': True,
            'credit_override_reason': self.override_reason,
            'credit_approval_requested': False,
        })
        self.env['inom.credit.audit']._log(
            self.partner_id, 'override',
            amount=self.over_amount,
            note=_("Override by %(user)s: %(reason)s",
                   user=self.env.user.name, reason=self.override_reason),
            document=order)
        order.message_post(body=_(
            "Credit block overridden by %(user)s. Reason: %(reason)s",
            user=self.env.user.name, reason=self.override_reason))
        return order.action_confirm()
