from odoo import Command, models, fields
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_rounding_method = fields.Boolean(
        string='Is Rounding Method?',
        default=False,
    )

    is_auto_rounding = fields.Boolean(
        string='Auto Apply Rounding On Select?',
        default=False,
    )

    def _create_payment_line(self, session, amount, account=None, message=None, partner=None, foreign_currency=None, amount_currency=None):
        # Rounding is not real money received: instead of an account.payment
        # (which needs a journal), post the difference on the Rounding Account.
        if self.is_rounding_method:
            return self._create_rounding_payment_line(session, amount, account, message, partner)
        return super()._create_payment_line(session, amount, account, message, partner, foreign_currency, amount_currency)

    def _create_rounding_payment_line(self, session, amount, account=None, message=None, partner=None):
        self.ensure_one()
        if session.currency_id.is_zero(amount):
            return self.env['account.move.line']

        rounding_account = session.config_id.rounding_account_id
        if not rounding_account:
            raise UserError(self.env._(
                "Please set a Rounding Account in the settings of %(config)s.",
                config=session.config_id.name,
            ))

        company = session.company_id
        journal = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(company),
            ('type', '=', 'general'),
        ], limit=1) or session.config_id.journal_id
        destination_account = account or self.receivable_account_id or session._get_receivable_account()
        date = fields.Date.context_today(self)
        balance = session.currency_id._convert(amount, company.currency_id, company, date)
        name = message or self.env._(
            '%(payment_method)s POS session %(session)s',
            payment_method=self.name,
            session=session.name,
        )

        move = self.env['account.move'].sudo().with_company(company).create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': date,
            'ref': name,
            'line_ids': [
                Command.create({
                    'name': name,
                    'account_id': destination_account.id,
                    'partner_id': partner.id if partner else False,
                    'currency_id': session.currency_id.id,
                    'amount_currency': -amount,
                    'balance': -balance,
                }),
                Command.create({
                    'name': name,
                    'account_id': rounding_account.id,
                    'currency_id': session.currency_id.id,
                    'amount_currency': amount,
                    'balance': balance,
                }),
            ],
        })
        move._post()
        return move.line_ids.filtered(lambda line: line.account_id == destination_account)
