# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AddWalletBalanceWizard(models.TransientModel):
    _name = 'add.wallet.balance.wizard'
    _description = 'Add Money to Wallet Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain=[('parent_id', '=', False)],
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    description = fields.Char(string='Memo', default=lambda self: _('Manual Wallet Recharge'))
    transaction_type = fields.Selection(
        selection=[
            ('credit', 'Add to Wallet'),
            ('debit', 'Remove from Wallet'),
        ],
        string='Operation',
        required=True,
        default='credit',
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.currency_id = self.env.company.currency_id

    def action_confirm(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Please enter a positive amount."))
        partner = self.partner_id.commercial_partner_id or self.partner_id
        transaction = self.env['website.wallet.transaction'].sudo().create({
            'partner_id': partner.id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'description': self.description or _('Manual Wallet Adjustment'),
        })
        transaction.action_confirm()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Wallet Transaction'),
            'res_model': 'website.wallet.transaction',
            'res_id': transaction.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
