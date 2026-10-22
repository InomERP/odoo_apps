from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PropertyDepositSettlement(models.TransientModel):
    _name = 'property.deposit.settlement'
    _description = 'Settle Security Deposit'

    contract_id = fields.Many2one('property.rental.contract', required=True, readonly=True)
    currency_id = fields.Many2one(related='contract_id.currency_id')
    deposit_held = fields.Monetary(related='contract_id.deposit_held', string='Deposit Held')
    line_ids = fields.One2many('property.deposit.settlement.line', 'settlement_id', string='Deductions')
    total_deducted = fields.Monetary(compute='_compute_totals')
    refund_amount = fields.Monetary(string='To Refund', compute='_compute_totals')

    @api.depends('line_ids.amount', 'deposit_held')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_deducted = sum(wizard.line_ids.mapped('amount'))
            wizard.refund_amount = wizard.deposit_held - wizard.total_deducted

    @api.constrains('line_ids')
    def _check_deductions(self):
        for wizard in self:
            if any(line.amount <= 0 for line in wizard.line_ids):
                raise ValidationError(self.env._("Each deduction must be a positive amount."))
            if wizard.currency_id.compare_amounts(wizard.total_deducted, wizard.deposit_held) > 0:
                raise ValidationError(self.env._(
                    "Deductions cannot exceed the deposit held. Invoice the extra amount separately."
                ))

    def action_settle(self):
        """ Create a draft credit note that releases the deposit held: the deposit line debits the
        deposit account, each deduction line credits its income account, and the total is owed to
        the tenant, to refund or to use against open invoices. """
        self.ensure_one()
        contract = self.contract_id
        contract._check_billing_rights()
        if contract.currency_id.compare_amounts(self.deposit_held, 0.0) <= 0:
            raise UserError(self.env._("No collected deposit is held for %(contract)s.", contract=contract.name))
        company = contract.company_id
        lines = [Command.create({
            'product_id': company._get_rental_product('deposit').id,
            'name': self.env._("Security deposit released, lease %(contract)s", contract=contract.name),
            'quantity': 1,
            'price_unit': self.deposit_held,
        })]
        deduction_product = company._get_rental_product('deduction')
        for line in self.line_ids:
            lines.append(Command.create({
                'product_id': deduction_product.id,
                'name': line.name,
                'quantity': 1,
                'price_unit': -line.amount,
            }))
        vals = {
            'move_type': 'out_refund',
            'partner_id': contract.tenant_id.id,
            'company_id': company.id,
            'currency_id': contract.currency_id.id,
            'invoice_origin': contract.name,
            'ref': self.env._("Deposit settlement of %(contract)s", contract=contract.name),
            'property_rental_contract_id': contract.id,
            'property_id': contract.property_id.id,
            'property_rental_move_kind': 'deposit_settlement',
            'invoice_line_ids': lines,
        }
        if company.rental_journal_id:
            vals['journal_id'] = company.rental_journal_id.id
        credit_note = self.env['account.move'].with_company(company).create(vals)
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_refund_type')
        action.update({'views': [(False, 'form')], 'res_id': credit_note.id, 'domain': [('id', '=', credit_note.id)]})
        return action


class PropertyDepositSettlementLine(models.TransientModel):
    _name = 'property.deposit.settlement.line'
    _description = 'Deposit Deduction'

    settlement_id = fields.Many2one('property.deposit.settlement', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='settlement_id.currency_id')
    name = fields.Char(string='Reason', required=True)
    amount = fields.Monetary(required=True)
