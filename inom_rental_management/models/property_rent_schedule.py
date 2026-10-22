from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

PERIOD_MONTHS = {'monthly': 1, 'quarterly': 3, 'half_yearly': 6, 'yearly': 12}


def months_between(start, end):
    """ Length of the inclusive period [start, end] in months, partial months prorated by day. """
    stop = end + relativedelta(days=1)
    months = 0
    while start + relativedelta(months=months + 1) <= stop:
        months += 1
    rest_start = start + relativedelta(months=months)
    month_days = ((rest_start + relativedelta(months=1)) - rest_start).days
    return months + (stop - rest_start).days / month_days


class PropertyRentSchedule(models.Model):
    _name = 'property.rent.schedule'
    _description = 'Rent Billing Schedule'
    _order = 'contract_id, period_start'
    _rec_name = 'period_start'

    contract_id = fields.Many2one('property.rental.contract', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='contract_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='contract_id.currency_id')
    property_id = fields.Many2one(related='contract_id.property_id', store=True, index=True)
    tenant_id = fields.Many2one(related='contract_id.tenant_id', store=True, index=True)
    user_id = fields.Many2one(related='contract_id.user_id', store=True, string='Responsible')
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    date_due = fields.Date(string='Due Date', required=True, index=True)
    amount = fields.Monetary(string='Rent', required=True)

    move_id = fields.Many2one(
        'account.move', string='Invoice', readonly=True, copy=False, index='btree_not_null', ondelete='restrict',
        help="Current invoice of this period. Earlier cancelled or credited invoices are kept in the history.",
    )
    move_ids = fields.One2many('account.move', 'property_rent_schedule_id', string='Invoice History')
    state = fields.Selection(
        selection=[
            ('pending', 'To Invoice'),
            ('draft', 'Draft Invoice'),
            ('invoiced', 'Invoiced'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        compute='_compute_state', store=True, index=True,
    )
    invoice_date_due = fields.Date(related='move_id.invoice_date_due', string='Invoice Due Date', store=True)
    due_reminder_sent = fields.Boolean(copy=False, readonly=True)
    amount_residual = fields.Monetary(related='move_id.amount_residual', string='Amount Due', store=True)

    _period_uniq = models.Constraint(
        'UNIQUE(contract_id, period_start)',
        'A rental period can appear only once in a billing schedule.',
    )

    @api.depends('move_id.state', 'move_id.payment_state', 'move_id.reversal_move_ids.state')
    def _compute_state(self):
        for line in self:
            move = line.move_id
            if not move:
                line.state = 'pending'
            elif move.state == 'cancel' or line._is_credited(move):
                line.state = 'cancelled'
            elif move.state == 'draft':
                line.state = 'draft'
            elif move.payment_state in ('paid', 'in_payment', 'reversed'):
                line.state = 'paid'
            else:
                line.state = 'invoiced'

    @staticmethod
    def _is_credited(move):
        """ Credited means reversed by a credit note of this invoice. An invoice settled with another
        credit note (a deposit used against rent, for example) is also 'reversed' in Odoo, but paid. """
        return move.payment_state == 'reversed' and bool(move.reversal_move_ids.filtered(lambda r: r.state == 'posted'))

    def _compute_display_name(self):
        for line in self:
            line.display_name = f'{line.contract_id.name}: {line.period_start} - {line.period_end}'

    # ------------------------------------------------------------------
    # Invoicing
    # ------------------------------------------------------------------
    def _lock_for_invoicing(self):
        """ Lock the lines, then re-read them. A concurrent transaction that invoiced the same
        line makes this one fail with a serialization error (and be retried), so a period is
        never invoiced twice. The unique index on account.move is the final guarantee. """
        if self:
            self.env.cr.execute('SELECT id FROM property_rent_schedule WHERE id IN %s FOR UPDATE', [tuple(self.ids)])
            self.invalidate_recordset(['move_id', 'state'])

    def _prepare_invoice_vals(self):
        self.ensure_one()
        contract = self.contract_id
        company = contract.company_id
        product = company._get_rental_product('rent')
        vals = {
            'move_type': 'out_invoice',
            'partner_id': contract.tenant_id.id,
            'company_id': company.id,
            'currency_id': contract.currency_id.id,
            'invoice_date': self.date_due,
            'invoice_origin': contract.name,
            'property_rental_contract_id': contract.id,
            'property_id': contract.property_id.id,
            'property_rent_schedule_id': self.id,
            'property_rental_move_kind': 'rent',
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
                'name': self.env._(
                    "Rent %(property)s, %(start)s to %(end)s",
                    property=contract.property_id.display_name, start=self.period_start, end=self.period_end,
                ),
                'quantity': 1,
                'price_unit': self.amount,
            })],
        }
        if company.rental_journal_id:
            vals['journal_id'] = company.rental_journal_id.id
        return vals

    def _create_invoices(self, allowed_states=('pending',)):
        """ Create one invoice per line in an allowed state. Lines are re-checked after locking,
        so running this twice, or concurrently, never creates a second invoice for a period. """
        # Write pending changes (an invoice just cancelled or credited) before the unique index is checked.
        self.env.flush_all()
        self._lock_for_invoicing()
        lines = self.filtered(lambda l: l.state in allowed_states and l.contract_id.state not in ('draft', 'approved', 'cancelled'))
        moves = self.env['account.move']
        for line in lines:
            move = self.env['account.move'].with_company(line.company_id).create(line._prepare_invoice_vals())
            line.sudo().move_id = move
            moves |= move
        to_post = moves.filtered(lambda m: m.company_id.rental_auto_post_invoices)
        if to_post:
            to_post.action_post()
        return moves

    def action_create_invoice(self):
        """ Invoice a period by hand: a period not yet invoiced, or again after its invoice was
        cancelled or credited. """
        if not self.env.user.has_group('account.group_account_invoice'):
            raise UserError(self.env._("You need Invoicing access to create rent invoices."))
        if any(line.state not in ('pending', 'cancelled') for line in self):
            raise UserError(self.env._("Only periods that are not invoiced, or whose invoice was cancelled, can be invoiced."))
        moves = self._create_invoices(allowed_states=('pending', 'cancelled'))
        if len(moves) == 1:
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
            action.update({'views': [(False, 'form')], 'res_id': moves.id, 'domain': [('id', '=', moves.id)]})
            return action
        return True

    @api.model
    def _get_due_lines(self, contracts=None):
        today = fields.Date.context_today(self)
        lines = self.browse()
        for company in (contracts.company_id if contracts else self.env['res.company'].sudo().search([])):
            domain = [
                ('company_id', '=', company.id),
                ('state', '=', 'pending'),
                ('date_due', '<=', today + relativedelta(days=company.rental_invoice_advance_days)),
                ('contract_id.state', 'in', ('running', 'expired', 'terminated', 'closed')),
            ]
            if contracts:
                domain.append(('contract_id', 'in', contracts.ids))
            lines |= self.search(domain)
        return lines

    @api.model
    def _cron_generate_rent_invoices(self):
        """ Daily job: invoice every due period that has never been invoiced. Idempotent. """
        lines = self.sudo()._get_due_lines()
        for company, company_lines in lines.grouped('company_id').items():
            company_lines.with_company(company)._create_invoices()
