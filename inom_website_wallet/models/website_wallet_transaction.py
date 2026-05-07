# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WebsiteWalletTransaction(models.Model):
    _name = 'website.wallet.transaction'
    _description = 'Wallet Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        index=True,
        domain=[('parent_id', '=', False)],
    )
    transaction_type = fields.Selection(
        selection=[
            ('credit', 'Credit'),
            ('debit', 'Debit'),
        ],
        string='Transaction Type',
        required=True,
        default='credit',
        tracking=True,
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    description = fields.Char(string='Memo', tracking=True)
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        readonly=True,
        copy=False,
    )
    account_move_id = fields.Many2one(
        'account.move',
        string='Invoice / Bill',
        readonly=True,
        copy=False,
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Accounting Entry',
        readonly=True,
        copy=False,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        compute='_compute_journal_id',
        store=False,
    )
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Payment Method',
        related='payment_id.payment_method_line_id',
        store=False,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Compute / constraints
    # ------------------------------------------------------------------
    @api.depends('payment_id')
    def _compute_journal_id(self):
        for rec in self:
            rec.journal_id = rec.payment_id.journal_id or False

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Wallet transaction amount must be strictly positive."))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'website.wallet.transaction'
                ) or _('New')
        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_(
                    "You cannot delete a confirmed wallet transaction (%s). "
                    "Please cancel it first.", rec.name
                ))
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.transaction_type == 'debit' and (
                rec.partner_id.wallet_balance - rec.amount
            ) < 0:
                raise UserError(_(
                    "Customer %s has insufficient wallet balance "
                    "(available: %s) for this debit of %s.",
                    rec.partner_id.display_name,
                    rec.partner_id.wallet_balance,
                    rec.amount,
                ))
            rec.state = 'confirmed'
            rec._create_accounting_entry()
            # invalidate to refresh wallet balance computation on partner
            rec.partner_id.invalidate_recordset(['wallet_balance', 'wallet_transaction_count'])
            rec._send_transaction_notification()
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                continue
            # reverse posted payment if any
            if rec.payment_id and rec.payment_id.state == 'paid':
                try:
                    rec.payment_id.action_draft()
                except Exception:
                    pass
                try:
                    rec.payment_id.action_cancel()
                except Exception:
                    pass
            rec.state = 'cancelled'
            rec.partner_id.invalidate_recordset(['wallet_balance', 'wallet_transaction_count'])
        return True

    def action_draft(self):
        for rec in self:
            if rec.state == 'cancelled':
                rec.state = 'draft'
                rec.partner_id.invalidate_recordset(['wallet_balance', 'wallet_transaction_count'])
        return True

    # ------------------------------------------------------------------
    # Accounting integration
    # ------------------------------------------------------------------
    def _get_wallet_journal(self):
        """Return (or create) a Wallet journal for the company.

        We use a cash-type journal named 'Wallet' to track the wallet
        liability towards customers.
        """
        self.ensure_one()
        Journal = self.env['account.journal'].sudo()
        company = self.company_id or self.env.company
        # Look for an existing journal flagged as wallet first
        journal = Journal.search([
            ('company_id', '=', company.id),
            ('is_wallet_journal', '=', True),
        ], limit=1)
        if journal:
            return journal
        # Fallback: search by code
        journal = Journal.search([
            ('company_id', '=', company.id),
            ('code', '=', 'WLLT'),
        ], limit=1)
        if journal:
            journal.is_wallet_journal = True
            return journal
        # Create one
        journal_vals = {
            'name': _('Wallet'),
            'code': 'WLLT',
            'type': 'cash',
            'company_id': company.id,
            'is_wallet_journal': True,
        }
        journal = Journal.create(journal_vals)
        return journal

    def _create_accounting_entry(self):
        """Create an account.payment when transaction is confirmed.

        Credit -> internal transfer from configured "destination" journal
                  (typically the customer's payment journal at recharge time)
                  to the Wallet journal. We model it as a simple "inbound"
                  customer payment on the Wallet journal so it shows up as
                  available outstanding credit.
        Debit  -> outbound payment from the Wallet journal (used to pay an
                  invoice or to release funds).
        """
        self.ensure_one()
        if self.payment_id:
            return self.payment_id

        Payment = self.env['account.payment'].sudo()
        wallet_journal = self._get_wallet_journal()

        payment_type = 'inbound' if self.transaction_type == 'credit' else 'outbound'
        partner_type = 'customer'

        memo = self.description or (
            _('Wallet Recharge - %s', self.name)
            if self.transaction_type == 'credit'
            else _('Wallet Usage - %s', self.name)
        )
        payment_vals = {
            'partner_id': self.partner_id.id,
            'partner_type': partner_type,
            'payment_type': payment_type,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'date': self.date,
            'journal_id': wallet_journal.id,
            'memo': memo,
            'company_id': self.company_id.id,
        }
        try:
            payment = Payment.create(payment_vals)
            payment.action_post()
            self.payment_id = payment.id
        except Exception:
            # If posting fails (chart of accounts issues etc.), keep the
            # transaction but don't block the wallet flow.
            pass
        return self.payment_id

    # ------------------------------------------------------------------
    # Mail
    # ------------------------------------------------------------------
    def _send_transaction_notification(self):
        """Send the appropriate notification email based on transaction type.

        Credit (recharge) -> 'mail_template_wallet_recharge'
        Debit (used)      -> 'mail_template_wallet_debit'
        """
        self.ensure_one()
        template_xmlid = (
            'inom_website_wallet.mail_template_wallet_recharge'
            if self.transaction_type == 'credit'
            else 'inom_website_wallet.mail_template_wallet_debit'
        )
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            _logger.warning(
                "Wallet notification template %s not found, cannot notify "
                "transaction %s", template_xmlid, self.name,
            )
            return
        if not self.partner_id.email:
            _logger.info(
                "Skipping wallet notification email for %s: customer %s has "
                "no email address.", self.name, self.partner_id.display_name,
            )
            return
        try:
            # force_send=True so the email leaves the system immediately
            # instead of waiting for the next mail-queue cron run.
            template.sudo().send_mail(self.id, force_send=True)
        except Exception as e:  # noqa: BLE001
            _logger.warning(
                "Failed to send wallet notification email for %s: %s",
                self.name, e,
            )

    # Backwards-compatible alias (used to be the only notification method)
    def _send_recharge_notification(self):
        return self._send_transaction_notification()

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_open_payment(self):
        self.ensure_one()
        if not self.payment_id:
            raise UserError(_("No accounting entry linked to this transaction."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.payment_id.id,
            'target': 'current',
        }

    def action_open_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }
