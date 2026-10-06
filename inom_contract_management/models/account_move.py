# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    contract_id = fields.Many2one(
        comodel_name='inom.contract',
        string='Contract',
        copy=False,
        index=True,
    )

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id and self.contract_id.partner_id:
            self.partner_id = self.contract_id.partner_id

    def action_apply_contract(self):
        self.ensure_one()
        contract = self.contract_id
        
        if not contract:
            raise UserError(_('Please select a contract first.'))
        lines = [Command.clear()]
        for line in contract.line_ids:
            lines.append(Command.create({
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'tax_ids': [Command.set(line.tax_ids.ids)],
            }))
        self.write({
            'partner_id': contract.partner_id.id,
            'ref': contract.name,
            'narration': contract.description,
            'invoice_payment_term_id': contract.payment_term_id.id,
            'invoice_line_ids': lines,
        })
        return True