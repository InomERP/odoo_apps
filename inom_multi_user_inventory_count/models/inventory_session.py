# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockInventoryCountSession(models.Model):
    _name = 'stock.inventory.count.session'
    _description = 'Inventory Count Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
    )
    inventory_count_id = fields.Many2one(
        'stock.inventory.count',
        string='Inventory Count',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='inventory_count_id.company_id',
        string='Company',
        store=True,
        index=True,
    )
    approver_id = fields.Many2one(
        related='inventory_count_id.approver_id',
        string='Approver',
        store=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Assigned User',
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
    )
    use_barcode_scanner = fields.Boolean(
        string='Use Barcode Scanner',
    )
    session_type = fields.Selection(
        selection=[
            ('single', 'Single Session'),
            ('multi', 'Multi Session'),
        ],
        string='Count Type',
    )
    barcode_scan = fields.Char(
        string='Scan Barcode',
        store=False,
        copy=False,
        help='Scan or type a product barcode to mark the matching '
             'line as scanned and increase its counted quantity.',
    )
    session_line_ids = fields.One2many(
        'stock.inventory.session.line',
        'session_id',
        string='Counting Lines',
        copy=True,
    )
    total_products = fields.Integer(
        string='Total Products',
        compute='_compute_line_counts',
        store=True,
    )
    total_scanned_products = fields.Integer(
        string='Scanned',
        compute='_compute_line_counts',
        store=True,
    )
    to_be_scanned = fields.Integer(
        string='To Be Scanned',
        compute='_compute_line_counts',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('done', 'Submitted'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )
    timer_start = fields.Datetime(
        string='Timer Start',
        copy=False,
        help='Technical field: timestamp when the running clock was '
             'last (re)started. Empty when the timer is paused.',
    )
    timer_elapsed = fields.Float(
        string='Elapsed Seconds',
        default=0.0,
        copy=False,
        help='Banked counting time in seconds (excludes the currently '
             'running interval).',
    )
    is_running = fields.Boolean(
        string='Timer Running',
        compute='_compute_is_running',
    )
    time_consumed_display = fields.Char(
        string='Time Consumed',
        compute='_compute_time_consumed_display',
    )
    submit_date = fields.Datetime(
        string='Submitted On',
        copy=False,
        readonly=True,
    )
    parent_session_id = fields.Many2one(
        'stock.inventory.count.session',
        string='Parent Session',
        copy=False,
        index=True,
        help='Set on a re-session: links back to the session it was '
             'created from.',
    )
    re_session_id = fields.Many2one(
        'stock.inventory.count.session',
        string='Re-Session',
        copy=False,
        help='The re-session created from the rejected lines of this session.',
    )
    pending_line_count = fields.Integer(
        string='Pending Lines',
        compute='_compute_line_review_counts',
    )
    approved_line_count = fields.Integer(
        string='Approved Lines',
        compute='_compute_line_review_counts',
    )
    rejected_line_count = fields.Integer(
        string='Rejected Lines',
        compute='_compute_line_review_counts',
    )
    lines_validated = fields.Boolean(
        string='Lines Validated',
        copy=False,
        default=False,
    )

    @api.depends('session_line_ids.state')
    def _compute_line_review_counts(self):
        for session in self:
            lines = session.session_line_ids
            session.pending_line_count = len(
                lines.filtered(lambda l: l.state == 'pending_review'))
            session.approved_line_count = len(
                lines.filtered(lambda l: l.state == 'approve'))
            session.rejected_line_count = len(
                lines.filtered(lambda l: l.state == 'reject'))

    @api.depends('session_line_ids', 'session_line_ids.scanned')
    def _compute_line_counts(self):
        for session in self:
            total = len(session.session_line_ids)
            scanned = len(session.session_line_ids.filtered('scanned'))
            session.total_products = total
            session.total_scanned_products = scanned
            session.to_be_scanned = total - scanned

    @api.depends('timer_start', 'state')
    def _compute_is_running(self):
        for session in self:
            session.is_running = bool(session.timer_start) \
                and session.state == 'in_progress'

    @api.depends('timer_elapsed', 'timer_start', 'state')
    def _compute_time_consumed_display(self):
        now = fields.Datetime.now()
        for session in self:
            seconds = session.timer_elapsed or 0.0
            if session.timer_start and session.state == 'in_progress':
                seconds += max((now - session.timer_start).total_seconds(), 0.0)
            seconds = int(seconds)
            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            session.time_consumed_display = '%02d:%02d:%02d' % (
                hours, minutes, secs)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'stock.inventory.count.session') or _('New')
        return super().create(vals_list)

    def unlink(self):
        for session in self:
            if session.state == 'done':
                raise UserError(_(
                    "A submitted session cannot be deleted."))
        return super().unlink()

    def action_open_scan_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scan & Count'),
            'res_model': 'stock.inventory.scan.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_session_id': self.id},
        }

    def _bank_elapsed(self):
        """Move the currently running interval into the banked elapsed time."""
        self.ensure_one()
        if self.timer_start:
            delta = (fields.Datetime.now() - self.timer_start).total_seconds()
            self.write({
                'timer_elapsed': (self.timer_elapsed or 0.0) + max(delta, 0.0),
                'timer_start': False,
            })

    def action_start(self):
        for session in self:
            if session.state == 'done':
                raise UserError(_(
                    "A submitted session cannot be restarted."))
            session.write({
                'state': 'in_progress',
                'timer_start': fields.Datetime.now(),
            })

    def action_pause(self):
        for session in self:
            if session.state != 'in_progress' or not session.timer_start:
                continue
            session._bank_elapsed()

    def action_submit(self):
        for session in self:
            if session.state not in ('draft', 'in_progress'):
                raise UserError(_(
                    "Only a draft or in-progress session can be submitted."))
            if session.timer_start:
                session._bank_elapsed()
            session.write({
                'state': 'done',
                'submit_date': fields.Datetime.now(),
            })

    @api.onchange('barcode_scan')
    def _onchange_barcode_scan(self):
        code = (self.barcode_scan or '').strip()
        if not code:
            return
        # Always clear the input so the next scan starts fresh.
        self.barcode_scan = False
        if self.state != 'in_progress':
            return {
                'warning': {
                    'title': _("Counting not started"),
                    'message': _(
                        "Please start the session before scanning products."),
                }
            }
        line = self.session_line_ids.filtered(
            lambda l: l.barcode and l.barcode == code)[:1]
        if not line:
            return {
                'warning': {
                    'title': _("Product not found"),
                    'message': _(
                        "No counting line matches the barcode '%s'.") % code,
                }
            }
        line.counted_qty += 1
        line.scanned = True

    # ------------------------------------------------------------------
    # Phase 4 - Session line review, validation and re-session
    # ------------------------------------------------------------------
    def _check_submitted(self):
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_(
                "Lines can only be reviewed on a submitted session."))

    def action_approve_all_lines(self):
        for session in self:
            session._check_submitted()
            session.session_line_ids.write({'state': 'approve'})

    def action_reject_pending_lines(self):
        for session in self:
            session._check_submitted()
            pending = session.session_line_ids.filtered(
                lambda l: l.state == 'pending_review')
            pending.write({'state': 'reject'})

    def action_validate_lines(self):
        self.ensure_one()
        self._check_submitted()
        if self.pending_line_count:
            raise UserError(_(
                "Please approve or reject all lines before validating "
                "the session."))
        if self.rejected_line_count:
            raise UserError(_(
                "Rejected lines found! Create a re-session to recount "
                "the rejected lines before validating this session."))
        self.lines_validated = True
        self.message_post(body=_("Session lines validated."))

    def action_create_re_session(self):
        self.ensure_one()
        self._check_submitted()
        if self.re_session_id:
            raise UserError(_(
                "A re-session has already been created for this session."))
        rejected_lines = self.session_line_ids.filtered(
            lambda l: l.state == 'reject')
        if not rejected_lines:
            raise UserError(_(
                "There are no rejected lines to create a re-session from."))
        new_session = self.create({
            'inventory_count_id': self.inventory_count_id.id,
            'user_id': self.user_id.id,
            'warehouse_id': self.warehouse_id.id,
            'location_id': self.location_id.id,
            'use_barcode_scanner': self.use_barcode_scanner,
            'session_type': self.session_type,
            'state': 'draft',
            'parent_session_id': self.id,
            'session_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'location_id': line.location_id.id,
            }) for line in rejected_lines],
        })
        self.re_session_id = new_session.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.inventory.count.session',
            'view_mode': 'form',
            'res_id': new_session.id,
            'target': 'current',
        }

    def action_view_re_session(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.inventory.count.session',
            'view_mode': 'form',
            'res_id': self.re_session_id.id,
            'target': 'current',
        }
