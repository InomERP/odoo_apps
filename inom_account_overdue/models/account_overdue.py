from odoo import models, fields, api


class AccountOverdue(models.Model):
    _name = 'account.overdue'
    _description = 'Account Overdue'

    invoice_id = fields.Many2one('account.move', string="Invoice")
    invoice_date = fields.Date(string="Invoice Date")
    date = fields.Date(string="Date")
    journal_id = fields.Many2one('account.journal', string="Journal")
    partner_id = fields.Many2one('res.partner', string="Partner")

    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill')
    ], string="Entry Type")

    label = fields.Char(string="Label")

    currency_id = fields.Many2one('res.currency', string="Currency")

    amount_currency = fields.Monetary(
        string="Amount in Currency",
        currency_field="currency_id"
    )

    debit = fields.Monetary(
        string="Pending",
        currency_field="currency_id"
    )

    credit = fields.Monetary(
        string="Paid",
        currency_field="currency_id"
    )

    tax_amount = fields.Monetary(
        string="Tax",
        currency_field="currency_id"
    )

    base_amount = fields.Monetary(
        string="Base Amount",
        currency_field="currency_id"
    )

    # NEW PROFESSIONAL MONITORING FIELDS
    days_overdue = fields.Integer(
        string="Days Overdue",
        compute="_compute_days_overdue",
        store=True
    )

    status = fields.Selection([
        ('normal', 'Normal'),
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ], string="Status", compute="_compute_status", store=True)

    # DAYS CALCULATION
    @api.depends('invoice_id')
    def _compute_days_overdue(self):
        today = fields.Date.today()

        for rec in self:
            if rec.invoice_id and rec.invoice_id.invoice_date_due:
                rec.days_overdue = (
                    today - rec.invoice_id.invoice_date_due
                ).days
            else:
                rec.days_overdue = 0

    # STATUS CALCULATION
    @api.depends('days_overdue')
    def _compute_status(self):
        for rec in self:
            if rec.days_overdue <= 5:
                rec.status = 'normal'
            elif rec.days_overdue <= 10:
                rec.status = 'warning'
            else:
                rec.status = 'critical'

    # CRON / HISTORY
    @api.model
    def check_overdue_invoices(self):
        today = fields.Date.today()

        invoices = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '=', 'posted'),
            ('invoice_date_due', '<', today)
        ])

        for inv in invoices:

            pending_amount = inv.amount_residual
            total_paid_till_now = inv.amount_total - inv.amount_residual

            previous_history = self.search([
                ('invoice_id', '=', inv.id)
            ])

            previous_paid_total = sum(previous_history.mapped('credit'))

            new_payment = total_paid_till_now - previous_paid_total

            last_entry = self.search(
                [('invoice_id', '=', inv.id)],
                order="id desc",
                limit=1
            )

            if (
                not last_entry
                or new_payment > 0
                or last_entry.debit != pending_amount
            ):
                self.create({
                    'invoice_id': inv.id,
                    'invoice_date': inv.invoice_date,
                    'date': fields.Date.today(),
                    'journal_id': inv.journal_id.id,
                    'partner_id': inv.partner_id.id,
                    'move_type': inv.move_type,
                    'label': inv.name,
                    'currency_id': inv.currency_id.id,

                    'amount_currency': pending_amount,
                    'debit': pending_amount,
                    'credit': max(new_payment, 0),

                    'tax_amount': inv.amount_tax,
                    'base_amount': inv.amount_untaxed,
                })


# from odoo import models, fields, api

# class AccountOverdue(models.Model):
#     _name = 'account.overdue'
#     _description = 'Account Overdue'

#     invoice_id = fields.Many2one('account.move', string="Invoice")
#     invoice_date = fields.Date(string="Invoice Date")
#     date = fields.Date(string="Date")
#     journal_id = fields.Many2one('account.journal', string="Journal")
#     partner_id = fields.Many2one('res.partner', string="Partner")

#     move_type = fields.Selection([
#         ('out_invoice', 'Customer Invoice'),
#         ('in_invoice', 'Vendor Bill')
#     ], string="Entry Type")

#     label = fields.Char(string="Label")
#     currency_id = fields.Many2one('res.currency', string="Currency")
#     amount_currency = fields.Monetary(
#         string="Amount in Currency",
#         currency_field="currency_id"
#     )
#     debit = fields.Monetary(
#         string="Pending",
#         currency_field="currency_id"
#     )
#     credit = fields.Monetary(
#         string="Paid",
#         currency_field="currency_id"
#     )
#     tax_amount = fields.Monetary(
#         string="Tax",
#         currency_field="currency_id"
#     )
#     base_amount = fields.Monetary(
#         string="Base Amount",
#         currency_field="currency_id"
#     )

#     @api.model
#     def check_overdue_invoices(self):
#         today = fields.Date.today()

#         invoices = self.env['account.move'].search([
#             ('move_type', 'in', ['out_invoice', 'in_invoice']),
#             ('state', '=', 'posted'),
#             ('invoice_date_due', '<', today)
#         ])

#         for inv in invoices:

#             pending_amount = inv.amount_residual
#             total_paid_till_now = inv.amount_total - inv.amount_residual

#             previous_history = self.search([
#                 ('invoice_id', '=', inv.id)
#             ])

#             previous_paid_total = sum(previous_history.mapped('credit'))

#             # exact new payment only
#             new_payment = total_paid_till_now - previous_paid_total

#             last_entry = self.search(
#                 [('invoice_id', '=', inv.id)],
#                 order="id desc",
#                 limit=1
#             )

#             # create history on:
#             # first overdue
#             # any payment
#             # pending amount changed
#             if (
#                 not last_entry
#                 or new_payment > 0
#                 or last_entry.debit != pending_amount
#             ):
#                 self.create({
#                     'invoice_id': inv.id,
#                     'invoice_date': inv.invoice_date,
#                     'date': fields.Date.today(),
#                     'journal_id': inv.journal_id.id,
#                     'partner_id': inv.partner_id.id,
#                     'move_type': inv.move_type,
#                     'label': inv.name,
#                     'currency_id': inv.currency_id.id,

#                     'amount_currency': pending_amount,
#                     'debit': pending_amount,
#                     'credit': max(new_payment, 0),

#                     'tax_amount': inv.amount_tax,
#                     'base_amount': inv.amount_untaxed,
#                 })