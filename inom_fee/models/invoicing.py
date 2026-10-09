import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InomFeeAccountLine(models.Model):
    """Issuing an instalment creates a real customer invoice.

    Up to now this model tracked what was owed and nothing reached the ledger,
    which meant the portal and the trial balance could never be reconciled.
    The money now lives in account.move, exactly once: this model schedules and
    explains, accounting records.
    """
    _inherit = 'inom.fee.account.line'

    partner_id = fields.Many2one(
        related='move_id.partner_id', string='Billed to', store=True, ondelete='set null',
        help='The guardian who pays, or the student where there is no guardian.')
    invoice_state = fields.Selection(
        related='move_id.state', string='Invoice status', store=True)

    # ------------------------------------------------------------------
    def _inom_action_issue_invoice(self, payload=None):
        self.ensure_one()
        if self.move_id:
            raise UserError(
                f'{self.name} was already invoiced as {self.move_id.name}. '
                f'Credit that invoice rather than issuing a second one.')
        if self.amount <= 0:
            raise UserError('There is nothing to invoice on this instalment.')

        move = self._inom_build_invoice()
        move.action_post()
        self.move_id = move
        return {'move_id': move.id, 'name': move.name,
                'partner': move.partner_id.display_name}

    def _inom_build_invoice(self):
        """Build the customer invoice for one instalment.

        Verify on target: account.move field names are stable across recent
        releases but accounting was reorganised in Odoo 20. Confirm
        `move_type`, `invoice_date_due` and the `invoice_line_ids` shape
        against the installed release before the first production run — a
        mistake here posts wrong numbers rather than raising.
        """
        self.ensure_one()
        account = self.account_id
        student = account.student_id
        partner = student._inom_billing_partner()

        # One line per head of fee, apportioned by this instalment's share of
        # the total. A single "Fee instalment 1" line balances just as well and
        # tells a parent querying the amount nothing at all.
        components = account.structure_id.component_ids
        payable = account.amount_billed
        share = (self.amount / payable) if payable else 0.0

        lines = []
        for component in components.sorted('sequence'):
            amount = round(component.amount * share, 2)
            if not amount:
                continue
            lines.append((0, 0, {
                'name': f'{component.name} — {self.name} — {account.year_id.name}',
                'quantity': 1.0,
                'price_unit': amount,
                'account_id': (component.account_id.id
                               or self._inom_income_account().id),
            }))

        if account.scholarship_id and account.amount_discount:
            # Shown as a negative line rather than a quietly reduced tuition
            # figure: a scholarship a parent cannot see on the invoice is one
            # the office will be asked to explain by phone.
            lines.append((0, 0, {
                'name': f'{account.scholarship_id.name} (applied pro rata)',
                'quantity': 1.0,
                'price_unit': -round(account.amount_discount * share, 2),
                'account_id': self._inom_income_account().id,
            }))

        Move = self.env['account.move']
        values = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,

            'invoice_date': fields.Date.context_today(self),
            'currency_id': self.currency_id.id,
            'company_id': account.company_id.id,
            'invoice_line_ids': lines,
        }
        # The optional trimmings, each only if the installed release has it.
        #
        # Accounting is the part of Odoo that moves most between releases —
        # `deprecated` vanished from account.account in 19 and took the whole
        # invoice down with it. These four are descriptive rather than
        # structural: an invoice without a narration is still a correct
        # invoice, and losing one is a far better outcome than losing the
        # posting.
        # Not the person who triggered it.
        #
        # Odoo defaults the salesperson to the creating user, and a student
        # pressing Pay is what creates their invoice — so it came out listing
        # the student as its own salesperson, on the document a parent reads.
        # A fee invoice has no salesperson; empty is more accurate than a name.
        #
        # Through the same presence check as the rest: the field belongs to
        # Sales, which an institution taking only fees need not have installed,
        # and naming an absent field raises rather than being ignored.
        for name, value in (('invoice_user_id', False),
                            ('invoice_date_due', self.due_date),
                            ('invoice_origin',
                             f'{student.enrolment_no} · {account.year_id.name}'),
                            ('narration',
                             f'{student.name} ({student.enrolment_no}) — '
                             f'{account.structure_id.name}')):
            if name in Move._fields:
                values[name] = value
            else:
                _logger.info(
                    'INOM fees: account.move has no "%s" in this release; the '
                    'invoice is posted without it', name)

        return Move.create(values)

    def _inom_income_account(self):
        """Fallback income account when a fee component names none.

        Raises rather than guessing: an invoice posted to an arbitrary account
        is worse than one that was never posted, because it looks finished.
        """
        self.ensure_one()
        company = self.account_id.company_id

        # Built from what the installed release actually has.
        #
        # `deprecated` was removed from account.account in Odoo 20, and a
        # domain naming a field that does not exist raises rather than
        # returning nothing — so the whole invoice failed on a filter that was
        # only ever a refinement. Accounting is the part of Odoo that moves
        # most between releases, and this module has to survive that.
        Account = self.env['account.account']
        domain = [('account_type', '=', 'income')]
        if 'company_ids' in Account._fields:
            domain.append(('company_ids', 'in', company.id))
        elif 'company_id' in Account._fields:
            domain.append(('company_id', '=', company.id))
        if 'deprecated' in Account._fields:
            domain.append(('deprecated', '=', False))

        account = Account.search(domain, limit=1)
        if not account:
            raise UserError(
                'No income account is configured for this campus, so the '
                'invoice cannot be posted. Set one on each fee component, or '
                'install a chart of accounts.')
        return account

    def _inom_action_send_invoice(self, payload=None):
        self.ensure_one()
        if not self.move_id:
            raise UserError('Issue the invoice before sending it.')
        if not self.move_id.partner_id.email:
            raise UserError(
                f'{self.move_id.partner_id.display_name} has no email address.')
        self.move_id.message_post(
            body=f'Fee invoice sent to {self.move_id.partner_id.email}.')
        return {'sent': True}

    @api.model
    def _inom_portal_fields(self):
        return super()._inom_portal_fields() + ['partner_id', 'invoice_state']


class InomFeeAccount(models.Model):
    _inherit = 'inom.fee.account'

    invoiced_count = fields.Integer(compute='_compute_invoiced', store=True)
    uninvoiced_amount = fields.Monetary(compute='_compute_invoiced', store=True)

    @api.depends('line_ids.move_id')
    def _compute_invoiced(self):
        for rec in self:
            invoiced = rec.line_ids.filtered('move_id')
            rec.invoiced_count = len(invoiced)
            rec.uninvoiced_amount = sum(
                (rec.line_ids - invoiced).mapped('amount'))

    def _inom_action_issue_due(self, payload=None):
        """Issue every instalment that is due and not yet invoiced.

        Scoped to what is due rather than the whole schedule: billing a
        student in July for an instalment payable next March is how a
        university ends up explaining its own invoices.
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        pending = self.line_ids.filtered(
            lambda l: not l.move_id and l.due_date <= today)
        if not pending:
            return {'issued': 0, 'message': 'Nothing is due for invoicing yet.'}
        for line in pending:
            line._inom_action_issue_invoice()
        return {'issued': len(pending),
                'message': f'{len(pending)} instalment(s) invoiced.'}

    @api.model
    def _inom_portal_fields(self):
        return super()._inom_portal_fields() + [
            'invoiced_count', 'uninvoiced_amount']


class InomFeeAccountLinePayment(models.Model):
    """The Pay action.

    Lives here rather than in inom_fee_online so the button exists whatever is
    installed; without the online module it says so plainly instead of the
    button silently doing nothing.
    """
    _inherit = 'inom.fee.account.line'

    def _inom_action_pay_link(self, payload=None):
        """Take payment for one instalment, raising the invoice if needed.

        Paying goes through an invoice: that is what a receipt is issued
        against and what reconciles against the bank. But requiring the
        accounts office to raise one *first* meant a student with three
        instalments on screen had no way to pay any of them until somebody
        else acted — a dead end with no indication of who to ask.

        So the invoice is raised on demand. The amounts come from the
        instalment, never from the request, so this creates nothing the
        accounts office could not have created itself with the same numbers.

        A policy worth confirming with the institution: some prefer invoices
        raised centrally in a batch, with students paying only what has been
        issued. Turn off **Raise fee invoices on demand** on the Institution
        for that.
        """
        self.ensure_one()
        if self.amount_due <= 0:
            raise UserError('This instalment is already settled.')

        if not self.move_id:
            # sudo(): the institution record is configuration every role needs
            # to read, and a student may not read it directly.
            institution = self.env['inom.institution'].sudo()._inom_current()
            on_demand = institution.fee_invoice_on_demand
            if not on_demand:
                raise UserError(
                    'No invoice has been raised for this instalment yet. The '
                    'accounts office raises them from Finance, and you will '
                    'be able to pay once yours is issued.')
            # sudo(): raising an invoice writes to account.move, which no
            # student may touch. What is written comes entirely from the
            # instalment they are already allowed to see.
            self.sudo()._inom_action_issue_invoice()
            self.invalidate_recordset(['move_id'])

        # sudo(), like every other read of the invoice from a student's own
        # instalment. I elevated the branch that *creates* the invoice and left
        # the one that reads its state — so paying worked right up to the check
        # that says whether it can be paid.
        if self.move_id.sudo().state != 'posted':
            raise UserError(
                'The invoice for this instalment is still a draft. The '
                'accounts office has to confirm it before it can be paid.')
        if self.amount_due <= 0:
            raise UserError('This instalment is already settled.')
        if 'payment.transaction' not in self.env:
            raise UserError(
                'Online payment is not installed on this system. Pay at the '
                'accounts office, or ask them to install the online fee '
                'payment module.')
        return {'open_url': f'/ums/pay/{self.id}'}


def _register_fee_reports():
    """Wire the receipt into the portal's report allow-list.

    Imported at module load so the controller knows the report exists without
    a database round trip on every request.
    """
    from odoo.addons.inom_portal.controllers.report import register_report
    register_report(
        'fee.receipt', 'inom_fee.action_report_fee_receipt',
        'inom.fee.account.line',
        # sudo(): naming the file reads the invoice, and the student
        # downloading their own receipt has no rights on account.move.
        lambda r: f'receipt-{(r.move_id.sudo().name or r.name).replace("/", "-")}')


_register_fee_reports()


class InomFeeAccountLineReport(models.Model):
    _inherit = 'inom.fee.account.line'

    def _inom_institution(self):
        """Delegated to the fee account, which carries the mixin.

        The line is a schedule row rather than a business object in its own
        right, so it has no company of its own to resolve from.
        """
        self.ensure_one()
        return self.account_id._inom_institution()

    def _inom_action_receipt(self, payload=None):
        self.ensure_one()
        return {'open_url': f'/ums/report/fee.receipt/{self.id}'}
