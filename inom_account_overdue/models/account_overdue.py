from odoo import models, fields, api

class AccountOverdue(models.Model):
    _name = 'account.overdue'
    _description = 'Account Overdue'

    invoice_id = fields.Many2one('account.move', string="Invoice")
    invoice_date = fields.Date(string="Invoice Date")
    date = fields.Date(string="Date")
    journal_id = fields.Many2one('account.journal', string="Journal")
    partner_id = fields.Many2one('res.partner', string="Partner")
    label = fields.Char(string="Label")
    currency_id = fields.Many2one('res.currency', string="Currency")
    amount_currency = fields.Monetary(string="Amount in Currency", currency_field="currency_id")
    debit = fields.Monetary(string="Pending", currency_field="currency_id")
    credit = fields.Monetary(string="Paid", currency_field="currency_id")
    tax_amount = fields.Monetary(string="Tax", currency_field="currency_id")
    base_amount = fields.Monetary(string="Base Amount", currency_field="currency_id")

    # CRON METHOD
    @api.model
    def check_overdue_invoices(self):

        today = fields.Date.today()

        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date_due', '<', today)
        ])

        for inv in invoices:

            # current pending
            debit = inv.amount_residual

            # total paid till now
            current_paid = inv.amount_total - inv.amount_residual

            # total previous paid history
            total_previous_paid = sum(
                self.search([
                    ('invoice_id', '=', inv.id)
                ]).mapped('credit')
            )

            # current exact payment
            new_payment = current_paid - total_previous_paid

            # last entry
            last_entry = self.search(
                [('invoice_id', '=', inv.id)],
                order="id desc",
                limit=1
            )

            # only create when payment happened
            if not last_entry or new_payment > 0 or last_entry.debit != debit:

                self.create({
                    'invoice_id': inv.id,
                    'invoice_date': inv.invoice_date,
                    'date': fields.Date.today(),
                    'journal_id': inv.journal_id.id,
                    'partner_id': inv.partner_id.id,
                    'label': inv.name,
                    'currency_id': inv.currency_id.id,

                    'amount_currency': debit,
                    'debit': debit,          # remaining
                    'credit': new_payment,   # exact payment only

                    'tax_amount': inv.amount_tax,
                    'base_amount': inv.amount_untaxed,
                })