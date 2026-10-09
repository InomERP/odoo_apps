from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InomBook(models.Model):
    """The title. One row per work, however many copies sit on the shelf."""
    _name = 'inom.book'
    _description = 'Library Title'
    _inherit = ['inom.mixin']
    _order = 'title'
    _rec_name = 'title'
    _rec_names_search = ['title', 'author', 'isbn']

    title = fields.Char(required=True, tracking=True)
    author = fields.Char(required=True)
    isbn = fields.Char(index=True)
    publisher = fields.Char()
    edition = fields.Char()
    year_published = fields.Integer()
    category = fields.Selection(
        [('textbook', 'Textbook'), ('reference', 'Reference'), ('journal', 'Journal'),
         ('thesis', 'Thesis'), ('fiction', 'General reading')],
        default='textbook', required=True)
    department_id = fields.Many2one('inom.department', index=True)
    shelf = fields.Char(help='Where it lives, e.g. CS-04-B.')

    copy_ids = fields.One2many('inom.book.copy', 'book_id', string='Copies')
    copies_total = fields.Integer(compute='_compute_copies', store=True)
    copies_available = fields.Integer(compute='_compute_copies', store=True)

    @api.depends('copy_ids.state')
    def _compute_copies(self):
        for rec in self:
            rec.copies_total = len(rec.copy_ids)
            rec.copies_available = len(rec.copy_ids.filtered(lambda c: c.state == 'available'))

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'title', 'author', 'isbn', 'publisher',
                'category', 'department_id', 'shelf', 'copies_total', 'copies_available']


class InomBookCopy(models.Model):
    """A physical copy, with its own barcode and its own condition.

    This is the level circulation actually happens at. A catalogue that tracks
    only "four available" cannot answer which four, where they are, or which
    one came back damaged.
    """
    _name = 'inom.book.copy'
    _description = 'Book Copy'
    _inherit = ['inom.mixin']
    _order = 'book_id, barcode'
    _rec_name = 'barcode'
    _rec_names_search = ['barcode', 'book_id.title', 'book_id.isbn']

    book_id = fields.Many2one('inom.book', required=True, ondelete='cascade', index=True)
    barcode = fields.Char(required=True, copy=False, index=True)
    acquired_on = fields.Date(default=fields.Date.context_today)
    condition = fields.Selection(
        [('new', 'New'), ('good', 'Good'), ('worn', 'Worn'), ('damaged', 'Damaged')],
        default='good', required=True)
    state = fields.Selection(
        [('available', 'Available'), ('issued', 'Issued'),
         ('reserved', 'Reserved'), ('lost', 'Lost'), ('withdrawn', 'Withdrawn')],
        default='available', required=True, index=True, tracking=True)

    _barcode_uniq = models.Constraint(
        'UNIQUE(barcode, company_id)',
        'That barcode is already in use.')

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'book_id', 'barcode', 'condition', 'state',
                'acquired_on']


class InomLoan(models.Model):
    _name = 'inom.loan'
    _description = 'Library Loan'
    _inherit = ['inom.mixin']
    _order = 'issued_on desc'
    _rec_name = 'display_name'
    _rec_names_search = ['student_id.name', 'student_id.enrolment_no',
                         'book_id.title', 'copy_id.barcode']

    copy_id = fields.Many2one('inom.book.copy', required=True, index=True)
    book_id = fields.Many2one(related='copy_id.book_id', store=True, index=True)
    student_id = fields.Many2one('inom.student', required=True, index=True)
    department_id = fields.Many2one(
        'inom.department', related='student_id.department_id', store=True, index=True)

    issued_on = fields.Date(required=True, default=fields.Date.context_today)
    due_on = fields.Date(required=True)
    returned_on = fields.Date(readonly=True, copy=False)
    days_overdue = fields.Integer(compute='_compute_overdue', store=True)
    fine_amount = fields.Monetary(compute='_compute_overdue', store=True)
    fine_paid = fields.Boolean(default=False, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id, required=True)

    state = fields.Selection(
        [('issued', 'Issued'), ('returned', 'Returned'), ('overdue', 'Overdue'),
         ('lost', 'Lost')],
        default='issued', required=True, index=True, tracking=True)

    #: Fine per day, in the company currency. A real deployment moves this onto
    #: a configuration record; it is a constant here so the module installs
    #: without a settings screen nobody has built yet.
    FINE_PER_DAY = 2.0

    @api.depends('due_on', 'returned_on', 'state')
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            end = rec.returned_on or today
            overdue = (end - rec.due_on).days if rec.due_on and end > rec.due_on else 0
            rec.days_overdue = overdue
            rec.fine_amount = overdue * rec.FINE_PER_DAY

    @api.constrains('due_on', 'issued_on')
    def _check_dates(self):
        for rec in self:
            if rec.due_on <= rec.issued_on:
                raise ValidationError('A loan must be due after it is issued.')

    @api.model_create_multi
    def create(self, vals_list):
        loans = super().create(vals_list)
        for loan in loans:
            if loan.copy_id.state != 'available':
                raise ValidationError(
                    f'{loan.copy_id.barcode} is not on the shelf — it is '
                    f'{loan.copy_id.state}.')
            loan.copy_id.state = 'issued'
        return loans

    @api.depends('student_id.name', 'book_id.title')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.student_id.name} · {rec.book_id.title}'

    # ------------------------------------------------------------------
    def _inom_action_return(self, payload=None):
        self.ensure_one()
        if self.state == 'returned':
            raise ValidationError('This copy has already come back.')
        self.write({'returned_on': fields.Date.context_today(self), 'state': 'returned'})
        self.copy_id.state = 'available'
        return {'fine': self.fine_amount}

    def _inom_action_mark_lost(self, payload=None):
        self.ensure_one()
        self.state = 'lost'
        self.copy_id.state = 'lost'
        return {'state': 'lost'}

    def _inom_action_settle_fine(self, payload=None):
        self.ensure_one()
        if not self.fine_amount:
            raise ValidationError('There is no fine on this loan.')
        self.fine_paid = True
        return {'fine_paid': True}

    @api.model
    def _inom_portal_fields(self):
        return ['id', 'display_name', 'copy_id', 'book_id', 'student_id',
                'issued_on', 'due_on', 'returned_on', 'days_overdue',
                'fine_amount', 'fine_paid', 'state', 'currency_id']
