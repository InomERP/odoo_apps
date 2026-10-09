from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InomFeeAccount(models.Model):
    """One student's fee position for one academic year.

    This model holds the *schedule*: which instalments are due, when, and how
    much of each remains. It deliberately does not hold a balance of its own —
    the money lives in account.move and account.payment, because a university
    that keeps a second ledger next to its accounting will eventually have two
    different answers to what a student owes, and no way to tell which is right.
    """
    _name = 'inom.fee.account'
    _description = 'Student Fee Account'
    _inherit = ['inom.mixin']
    _order = 'year_id desc, student_id'
    _rec_name = 'display_name'
    _rec_names_search = ['student_id.name', 'student_id.enrolment_no',
                         'year_id.name']

    student_id = fields.Many2one('inom.student', required=True, index=True,
                                 ondelete='cascade', tracking=True)
    department_id = fields.Many2one(
        'inom.department', related='student_id.department_id', store=True, index=True,
        ondelete='set null')
    year_id = fields.Many2one('inom.academic.year', required=True, index=True,
                              ondelete='restrict', tracking=True)
    structure_id = fields.Many2one('inom.fee.structure', required=True,
                                   ondelete='restrict', tracking=True)
    scholarship_id = fields.Many2one('inom.scholarship', ondelete='set null', tracking=True)

    line_ids = fields.One2many('inom.fee.account.line', 'account_id', string='Instalments')
    currency_id = fields.Many2one(related='structure_id.currency_id', store=True,
                                  ondelete='set null')

    amount_gross = fields.Monetary(compute='_compute_amounts', store=True)
    amount_discount = fields.Monetary(compute='_compute_amounts', store=True)
    amount_billed = fields.Monetary(compute='_compute_amounts', store=True,
                                    string='Total payable')
    amount_paid = fields.Monetary(compute='_compute_amounts', store=True)
    amount_due = fields.Monetary(compute='_compute_amounts', store=True)

    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'Open'), ('partial', 'Partly paid'),
         ('paid', 'Paid'), ('overdue', 'Overdue')],
        compute='_compute_state', store=True, index=True)

    _student_year_uniq = models.Constraint(
        'UNIQUE(student_id, year_id, company_id)',
        'This student already has a fee account for that academic year.')

    @api.depends('student_id.name', 'year_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.student_id.name} · {rec.year_id.name}'

    # Computed *and stored*: the finance dashboards aggregate these across every
    # student. Recomputing live is fine at 700 students and is not at 20,000.
    @api.depends('structure_id.total_amount', 'scholarship_id',
                 'line_ids.amount', 'line_ids.amount_paid')
    def _compute_amounts(self):
        for rec in self:
            gross = rec.structure_id.total_amount
            discount = 0.0
            if rec.scholarship_id:
                if rec.scholarship_id.kind == 'percent':
                    discount = gross * rec.scholarship_id.value / 100.0
                else:
                    discount = min(rec.scholarship_id.value, gross)
            rec.amount_gross = gross
            rec.amount_discount = discount
            rec.amount_billed = gross - discount
            rec.amount_paid = sum(rec.line_ids.mapped('amount_paid'))
            rec.amount_due = rec.amount_billed - rec.amount_paid

    @api.depends('amount_due', 'amount_paid', 'line_ids.due_date', 'line_ids.amount_paid')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.line_ids:
                rec.state = 'draft'
            elif rec.amount_due <= 0:
                rec.state = 'paid'
            elif any(line.due_date and line.due_date < today and line.amount_due > 0
                     for line in rec.line_ids):
                rec.state = 'overdue'
            elif rec.amount_paid > 0:
                rec.state = 'partial'
            else:
                rec.state = 'open'

    # ------------------------------------------------------------------
    def _inom_action_generate_schedule(self, payload=None):
        """Turn the structure's instalment template into dated lines."""
        self.ensure_one()
        if self.line_ids:
            raise ValidationError('This fee account already has a schedule. '
                                  'Archive it and create a new one instead.')
        if self.structure_id.state != 'published':
            raise ValidationError('Publish the fee structure before applying it.')

        start = self.year_id.date_start
        payable = self.amount_billed
        lines = []
        for instalment in self.structure_id.instalment_ids.sorted('sequence'):
            lines.append({
                'account_id': self.id,
                'name': instalment.name,
                'amount': payable * instalment.percentage / 100.0,
                'due_date': start + relativedelta(days=instalment.due_offset_days),
            })
        if not lines:
            # No instalment template: bill the whole amount at the start of the year.
            lines = [{'account_id': self.id, 'name': 'Full fee',
                      'amount': payable, 'due_date': start}]
        self.env['inom.fee.account.line'].create(lines)
        return {'lines': len(lines)}

    def _inom_action_print(self, payload=None):
        """Hand back a URL rather than a PDF.

        Same shape as the fee receipt and the structure sheet: the detail page
        follows `open_url`, and the report controller checks the caller's own
        rights on the record before it renders anything — so a student printing
        their own statement goes through the same route the accounts office
        does, and sees only their own.
        """
        self.ensure_one()
        return {'open_url': f'/ums/report/fee.account/{self.id}'}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'student_id', 'department_id', 'year_id',
                'structure_id', 'scholarship_id', 'amount_billed', 'amount_paid',
                'amount_due', 'state', 'currency_id']


def _register_fee_account_report():
    """Wire the fee statement into the portal's report allow-list."""
    from odoo.addons.inom_portal.controllers.report import register_report
    register_report(
        'fee.account', 'inom_fee.action_report_fee_account',
        'inom.fee.account',
        lambda r: f'fee-statement-'
                  f'{(r.student_id.enrolment_no or str(r.id)).replace("/", "-")}')


_register_fee_account_report()


class InomFeeAccountLine(models.Model):
    _name = 'inom.fee.account.line'
    _description = 'Fee Instalment Due'
    _order = 'due_date, id'

    account_id = fields.Many2one(
        'inom.fee.account', required=True, ondelete='cascade', index=True)
    student_id = fields.Many2one(related='account_id.student_id', store=True, index=True,
                                 ondelete='set null')
    name = fields.Char(required=True)
    amount = fields.Monetary(required=True)
    amount_paid = fields.Monetary(compute='_compute_paid', store=True)
    amount_due = fields.Monetary(compute='_compute_paid', store=True)
    due_date = fields.Date(required=True, index=True)
    currency_id = fields.Many2one(related='account_id.currency_id', store=True,
                                  ondelete='set null')

    move_id = fields.Many2one(
        'account.move', string='Invoice', ondelete='set null', copy=False,
        help='Raised in accounting when the instalment is issued. The invoice, '
             'not this line, is what the student actually owes.')

    state = fields.Selection(
        [('pending', 'Pending'), ('issued', 'Issued'), ('paid', 'Paid'),
         ('overdue', 'Overdue')],
        compute='_compute_state', store=True, index=True)

    @api.depends('move_id.amount_residual', 'move_id.state', 'amount')
    def _compute_paid(self):
        """How much of this instalment has been settled.

        The invoice is read with sudo. A portal user has no rights on
        account.move, and this compute runs while a student is reading their
        own instalments — so their own balance was computed from a record they
        may not open, and the read failed on the technical record behind it.

        Nothing about the invoice is exposed here; two figures come out of it
        and both are already on the instalment the student is looking at.
        """
        for rec in self:
            # sudo(): read-only access to the invoice's state and residual, so a
            # portal student can see their own balance (see docstring above).
            move = rec.move_id.sudo()
            if move and move.state == 'posted':
                rec.amount_paid = rec.amount - move.amount_residual
            else:
                rec.amount_paid = 0.0
            rec.amount_due = rec.amount - rec.amount_paid

    @api.depends('amount_due', 'due_date', 'move_id.state')
    def _compute_state(self):
        # Same reasoning as _compute_paid: the state of the invoice is read
        # with sudo, and only to decide what to show on the instalment.
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.amount_due <= 0 and rec.move_id:
                rec.state = 'paid'
            elif rec.due_date and rec.due_date < today:
                rec.state = 'overdue'
            elif rec.move_id:
                rec.state = 'issued'
            else:
                rec.state = 'pending'

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'name', 'student_id', 'amount', 'amount_paid',
                'amount_due', 'due_date', 'state', 'move_id', 'currency_id']
