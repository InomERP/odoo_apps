# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomCostEstimate(models.Model):
    _name = 'inom.cost.estimate'
    _description = 'Job Cost Estimate'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
                                 tracking=True)
    category_id = fields.Many2one('inom.cost.category', string='Job Category',
                                  tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible',
                              default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id,
        help='Currency of this estimate. Defaults to the company currency but '
             'can be changed for foreign-currency customers.')
    date_estimate = fields.Date(string='Estimate Date',
                                default=fields.Date.context_today, tracking=True)
    date_expiry = fields.Date(string='Expiry Date', copy=False)
    reference = fields.Char(string='Customer Reference')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('converted', 'Converted'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, copy=False)

    # ---- Premium: Revision / Versioning ----
    revision = fields.Integer(string='Revision', default=0, copy=False)
    origin_estimate_id = fields.Many2one('inom.cost.estimate',
                                         string='Original Estimate', copy=False)
    revision_ids = fields.One2many('inom.cost.estimate', 'origin_estimate_id',
                                   string='Revisions')
    revision_count = fields.Integer(compute='_compute_revision_count')

    # ---- Premium: Load from template ----
    template_id = fields.Many2one('inom.cost.template', string='Load From Template')

    # ---- Cost lines ----
    material_line_ids = fields.One2many('inom.cost.material.line', 'estimate_id',
                                        string='Materials', copy=True)
    labour_line_ids = fields.One2many('inom.cost.labour.line', 'estimate_id',
                                      string='Manpower', copy=True)
    equipment_line_ids = fields.One2many('inom.cost.equipment.line', 'estimate_id',
                                         string='Equipment', copy=True)
    overhead_line_ids = fields.One2many('inom.cost.overhead.line', 'estimate_id',
                                        string='Indirect Costs', copy=True)

    # ---- Amounts ----
    amount_material = fields.Monetary(compute='_compute_amounts', store=True,
                                      string='Material Cost')
    amount_labour = fields.Monetary(compute='_compute_amounts', store=True,
                                    string='Manpower Cost')
    amount_equipment = fields.Monetary(compute='_compute_amounts', store=True,
                                       string='Equipment Cost')
    amount_overhead = fields.Monetary(compute='_compute_amounts', store=True,
                                      string='Indirect Cost')
    amount_cost = fields.Monetary(compute='_compute_amounts', store=True,
                                  string='Total Cost')

    # ---- Premium: Markup & Margin ----
    markup_percent = fields.Float(string='Markup (%)', default=0.0, tracking=True)
    discount_percent = fields.Float(string='Discount (%)', default=0.0, tracking=True)
    amount_discount = fields.Monetary(compute='_compute_amounts', store=True,
                                      string='Discount')
    amount_sell = fields.Monetary(compute='_compute_amounts', store=True,
                                  string='Selling Price')
    amount_margin = fields.Monetary(compute='_compute_amounts', store=True,
                                    string='Margin')
    margin_percent = fields.Float(compute='_compute_amounts', store=True,
                                  string='Margin (%)')

    tax_ids = fields.Many2many('account.tax', string='Taxes',
                               domain=[('type_tax_use', '=', 'sale')])
    amount_tax = fields.Monetary(compute='_compute_amounts', store=True,
                                 string='Tax Amount')
    amount_rounding = fields.Monetary(compute='_compute_amounts', store=True,
                                      string='Rounding')
    amount_total = fields.Monetary(compute='_compute_amounts', store=True,
                                   string='Total')

    # ---- Sale link ----
    sale_order_id = fields.Many2one('sale.order', string='Quotation', copy=False)
    sale_count = fields.Integer(compute='_compute_sale_count')

    # ---- Premium: Cost control (estimated vs actual) ----
    project_id = fields.Many2one(
        'project.project', string='Project', tracking=True,
        help='Selecting a project fills in its analytic account automatically.')
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account', copy=False,
        tracking=True,
        help='Actual costs and revenues posted to this analytic account are '
             'compared against the estimated cost.')
    actual_cost = fields.Monetary(compute='_compute_actuals', string='Actual Cost')
    actual_revenue = fields.Monetary(compute='_compute_actuals',
                                     string='Actual Revenue')
    variance_amount = fields.Monetary(compute='_compute_actuals',
                                      string='Cost Variance')
    variance_percent = fields.Float(compute='_compute_actuals',
                                    string='Variance (%)')
    rate_card_id = fields.Many2one(
        'inom.rate.card', string='Rate Card', copy=True,
        help='Default rate card. New material and manpower lines take their '
             'rate from it; each line can still override.')
    budget_amount = fields.Monetary(
        string='Budget', copy=False,
        help="The customer's approved budget for this job. Set it to "
             "compare your estimated cost against what the client agreed to spend.")
    budget_variance = fields.Monetary(
        compute='_compute_budget', string='Budget Variance', store=True,
        help='Budget minus estimated cost. Positive means you are within budget.')
    budget_variance_percent = fields.Float(
        compute='_compute_budget', string='Budget Variance %', store=True)
    is_over_budget = fields.Boolean(
        compute='_compute_budget', string='Over Budget', store=True)
    analytic_line_count = fields.Integer(compute='_compute_actuals',
                                         string='Analytic Items')

    # ---- Premium: Customer portal approval ----
    signature = fields.Binary(string='Signature', copy=False, attachment=True,
                              help='Drawn by the customer when accepting online.')
    signed_by = fields.Char(string='Signed By', copy=False)
    signed_on = fields.Datetime(string='Signed On', copy=False)

    # Drawings, site photos, spec sheets and client mark-ups. Kept as an
    # explicit many2many rather than reusing the chatter's attachments, so
    # that project documents stay separate from whatever happens to have been
    # emailed back and forth, and survive a revision copy.
    document_ids = fields.Many2many(
        'ir.attachment', 'inom_cost_estimate_document_rel',
        'estimate_id', 'attachment_id', string='Documents', copy=True)
    document_count = fields.Integer(compute='_compute_document_count',
                                    string='Document Count')

    suggested_markup = fields.Float(compute='_compute_benchmarks',
                                    string='Suggested Markup (%)')
    suggestion_hint = fields.Char(compute='_compute_benchmarks')
    similar_count = fields.Integer(compute='_compute_benchmarks',
                                   string='Similar Jobs')
    cost_benchmark = fields.Monetary(compute='_compute_benchmarks',
                                     string='Similar Jobs Average Cost')
    cost_gap_percent = fields.Float(compute='_compute_benchmarks',
                                    string='Vs Similar Jobs (%)')

    loss_reason_id = fields.Many2one('inom.cost.loss.reason',
                                     string='Loss Reason', copy=False,
                                     tracking=True)
    loss_note = fields.Text(string='Loss Details', copy=False)

    revision_note = fields.Text(
        string='Revision Note', copy=False,
        help='Why this revision was raised. Shown on the estimate and in the '
             'revision history.')
    approval_log_ids = fields.One2many('inom.cost.approval.log', 'estimate_id',
                                       string='Approval History', copy=False)
    is_expired = fields.Boolean(compute='_compute_is_expired',
                                string='Expired')

    duration_days = fields.Float(
        string='Estimated Duration (days)',
        help='Working days the job is expected to take. Printed on the '
             'estimate so the customer sees the timeline alongside the price.')
    progress = fields.Float(compute='_compute_progress', string='Progress')

    note = fields.Html(string='Notes')
    terms = fields.Text(string='Terms & Conditions')

    # Fields that decide what the customer pays, or who pays it. Once an
    # estimate is approved these are frozen: the approval, and any quotation
    # raised from it, were granted against specific figures. Everything else
    # (notes, dates, responsible, project) stays editable, so the lock never
    # gets in the way of ordinary housekeeping.
    _INOM_LOCKED_FIELDS = frozenset((
        'material_line_ids', 'labour_line_ids', 'equipment_line_ids',
        'overhead_line_ids', 'markup_percent', 'discount_percent',
        'tax_ids', 'partner_id', 'currency_id', 'company_id',
    ))
    _INOM_LOCKED_STATES = ('approved', 'converted')

    def write(self, vals):
        if not self.env.context.get('inom_allow_locked_write'):
            touched = self._INOM_LOCKED_FIELDS.intersection(vals)
            if touched:
                for rec in self:
                    if rec.state not in rec._INOM_LOCKED_STATES:
                        continue
                    if rec.state == 'converted':
                        raise UserError(_(
                            'Estimate %(ref)s has been converted into quotation '
                            '%(order)s, so its pricing can no longer be changed. '
                            'Use New Revision to quote different figures.',
                            ref=rec.name,
                            order=rec.sale_order_id.display_name or '-'))
                    raise UserError(_(
                        'Estimate %(ref)s is approved, so its pricing can no '
                        'longer be changed. Use New Revision to quote '
                        'different figures, or reset it to draft first.',
                        ref=rec.name))
        if 'state' in vals:
            self._log_state_change(vals['state'])
        return super().write(vals)

    def _log_state_change(self, new_state):
        """Write the audit row before the state actually moves.

        Called from write() rather than from each button so that portal
        acceptance, server actions and imports are captured too.
        """
        labels = dict(self.fields_get(['state'])['state']['selection'])
        rows = []
        for rec in self:
            if rec.state == new_state:
                continue
            rows.append({
                'estimate_id': rec.id,
                'state_from': labels.get(rec.state, rec.state),
                'state_to': labels.get(new_state, new_state),
                'amount_total': rec.amount_total,
            })
        if rows:
            self.env['inom.cost.approval.log'].sudo().create(rows)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('material_line_ids.price_subtotal', 'material_line_ids.price_sell',
                 'labour_line_ids.price_subtotal', 'labour_line_ids.price_sell',
                 'equipment_line_ids.price_subtotal', 'equipment_line_ids.price_sell',
                 'material_line_ids.price_gross', 'labour_line_ids.price_gross',
                 'equipment_line_ids.price_gross', 'overhead_line_ids.price_gross',
                 'discount_percent',
                 'overhead_line_ids.amount', 'overhead_line_ids.price_sell',
                 'markup_percent', 'tax_ids')
    def _compute_amounts(self):
        for rec in self:
            mat = sum(rec.material_line_ids.mapped('price_subtotal'))
            lab = sum(rec.labour_line_ids.mapped('price_subtotal'))
            eqp = sum(rec.equipment_line_ids.mapped('price_subtotal'))
            ovh = sum(rec.overhead_line_ids.mapped('amount'))
            cost = mat + lab + eqp + ovh
            # Selling price rolls up per line so that lines carrying their own
            # markup are respected instead of a single header-level factor.
            sell = (sum(rec.material_line_ids.mapped('price_sell'))
                    + sum(rec.labour_line_ids.mapped('price_sell'))
                    + sum(rec.equipment_line_ids.mapped('price_sell'))
                    + sum(rec.overhead_line_ids.mapped('price_sell')))
            gross = (sum(rec.material_line_ids.mapped('price_gross'))
                     + sum(rec.labour_line_ids.mapped('price_gross'))
                     + sum(rec.equipment_line_ids.mapped('price_gross'))
                     + sum(rec.overhead_line_ids.mapped('price_gross')))
            margin = sell - cost
            # Tax is computed line by line, exactly as the quotation will do
            # it after conversion. Taxing the aggregate instead would drift
            # from the order total once several taxes, price-included taxes
            # or per-line rounding are involved.
            tax = 0.0
            if rec.tax_ids:
                for lines in (rec.material_line_ids, rec.labour_line_ids,
                              rec.equipment_line_ids, rec.overhead_line_ids):
                    for line in lines:
                        if not line.price_sell:
                            continue
                        res = rec.tax_ids.compute_all(
                            line.price_unit_sell * line._get_discount_factor(),
                            currency=rec.currency_id,
                            quantity=line._get_sell_quantity() or 1.0,
                            partner=rec.partner_id)
                        tax += res['total_included'] - res['total_excluded']
            rec.amount_material = mat
            rec.amount_labour = lab
            rec.amount_equipment = eqp
            rec.amount_overhead = ovh
            rec.amount_cost = cost
            rec.amount_discount = gross - sell
            rec.amount_sell = sell
            rec.amount_margin = margin
            rec.margin_percent = (margin / sell * 100.0) if sell else 0.0
            rec.amount_tax = tax
            raw_total = sell + tax
            step = rec._get_rounding_step()
            if step:
                rounded = round(raw_total / step) * step
                rec.amount_rounding = rounded - raw_total
                rec.amount_total = rounded
            else:
                rec.amount_rounding = 0.0
                rec.amount_total = raw_total

    @api.onchange('category_id')
    def _onchange_category_id_template(self):
        """Offer the template most often used for this job category.

        Only a suggestion: the field is filled, nothing is loaded until the
        user presses Load, so an unwanted guess costs one click to undo.
        """
        for rec in self:
            if not rec.category_id or rec.template_id:
                continue
            templates = rec.env['inom.cost.template'].search(
                [('category_id', '=', rec.category_id.id)])
            if not templates:
                continue
            usage = dict(rec.env['inom.cost.estimate']._read_group(
                [('template_id', 'in', templates.ids)],
                groupby=['template_id'], aggregates=['__count']))
            rec.template_id = max(
                templates, key=lambda t: usage.get(t, 0))

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Pull the project's analytic account across.

        The field holding it was renamed between Odoo versions, so both names
        are probed rather than assuming one.
        """
        for rec in self:
            if not rec.project_id:
                continue
            for fname in ('account_id', 'analytic_account_id'):
                if fname in rec.project_id._fields:
                    account = rec.project_id[fname]
                    if account:
                        rec.analytic_account_id = account
                    break

    @api.depends('budget_amount', 'amount_cost')
    def _compute_budget(self):
        """Compare the customer's approved budget with our estimated cost."""
        for rec in self:
            rec.budget_variance = rec.budget_amount - rec.amount_cost
            rec.budget_variance_percent = (
                rec.budget_variance / rec.budget_amount
                if rec.budget_amount else 0.0)
            rec.is_over_budget = bool(rec.budget_amount) and rec.amount_cost > rec.budget_amount

    @api.depends('analytic_account_id', 'analytic_account_id.line_ids.amount',
                 'amount_cost')
    def _compute_actuals(self):
        """Roll up real postings on the analytic account.

        Analytic lines carry costs as negative amounts and revenues as
        positive ones, so the two are split rather than netted off.
        """
        AnalyticLine = self.env['account.analytic.line'].sudo()
        accounts = self.mapped('analytic_account_id')
        totals = {}
        if accounts:
            # Two grouped reads instead of loading every analytic line into
            # Python. On a job with a year of timesheets and vendor bills that
            # is the difference between a form that opens and one that stalls.
            field = ('account_id' if 'account_id' in AnalyticLine._fields
                     else 'auto_account_id')
            for sign, key in ((-1, 'cost'), (1, 'revenue')):
                domain = [(field, 'in', accounts.ids)]
                domain.append((
                    'amount', '<' if sign < 0 else '>=', 0.0))
                for account, amount, count in AnalyticLine._read_group(
                        domain, groupby=[field],
                        aggregates=['amount:sum', '__count']):
                    bucket = totals.setdefault(account.id, {
                        'cost': 0.0, 'revenue': 0.0, 'count': 0})
                    bucket[key] = -amount if sign < 0 else amount
                    bucket['count'] += count
        for rec in self:
            bucket = totals.get(rec.analytic_account_id.id,
                                {'cost': 0.0, 'revenue': 0.0, 'count': 0})
            cost = bucket['cost']
            rec.actual_cost = cost
            rec.actual_revenue = bucket['revenue']
            rec.analytic_line_count = bucket['count']
            # Positive variance = came in under the estimate.
            rec.variance_amount = rec.amount_cost - cost
            rec.variance_percent = (
                (rec.amount_cost - cost) / rec.amount_cost * 100.0
            ) if rec.amount_cost else 0.0

    _PROGRESS_BY_STATE = {
        'draft': 10.0,
        'confirmed': 40.0,
        'approved': 75.0,
        'converted': 100.0,
        'rejected': 100.0,
    }

    def _get_rounding_step(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'inom_job_cost_estimation.rounding_step')
        try:
            return float(param or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _get_similar_domain(self):
        """Decided estimates in the same job category.

        Only approved and converted ones count: a draft that was never priced
        seriously would drag the averages around.
        """
        self.ensure_one()
        if not self.category_id:
            return None
        domain = [
            ('category_id', '=', self.category_id.id),
            ('state', 'in', ('approved', 'converted')),
            ('company_id', '=', self.company_id.id),
        ]
        if isinstance(self.id, int):
            domain.append(('id', '!=', self.id))
        return domain

    @api.depends('category_id', 'amount_cost', 'company_id')
    def _compute_benchmarks(self):
        for rec in self:
            rec.similar_count = 0
            rec.cost_benchmark = 0.0
            rec.cost_gap_percent = 0.0
            rec.suggested_markup = rec.category_id.default_markup or 0.0
            rec.suggestion_hint = False

            domain = rec._get_similar_domain()
            if domain is None:
                continue
            groups = rec.env['inom.cost.estimate']._read_group(
                domain, groupby=[],
                aggregates=['__count', 'markup_percent:avg', 'amount_cost:avg'])
            count, avg_markup, avg_cost = (groups[0] if groups else (0, 0.0, 0.0))
            rec.similar_count = count or 0
            rec.cost_benchmark = avg_cost or 0.0
            if count and avg_cost and rec.amount_cost:
                rec.cost_gap_percent = (
                    (rec.amount_cost - avg_cost) / avg_cost * 100.0)
            if count >= 3 and avg_markup:
                rec.suggested_markup = avg_markup
                rec.suggestion_hint = _(
                    'Average of %(n)s similar %(cat)s jobs',
                    n=count, cat=rec.category_id.name)
            elif rec.category_id.default_markup:
                rec.suggestion_hint = _('Job category default')

    def action_apply_suggested_markup(self):
        self.ensure_one()
        if not self.suggested_markup:
            raise UserError(_('There is no markup to suggest yet.'))
        self.markup_percent = self.suggested_markup

    def action_view_similar(self):
        self.ensure_one()
        domain = self._get_similar_domain()
        if domain is None:
            raise UserError(_(
                'Set a job category first - similar jobs are matched on it.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Similar Jobs'),
            'res_model': 'inom.cost.estimate',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'create': False},
        }

    @api.depends('date_expiry', 'state')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expired = bool(
                rec.date_expiry and rec.date_expiry < today
                and rec.state in ('draft', 'confirmed', 'approved'))

    @api.model
    def _cron_notify_expired(self):
        """Daily nudge on estimates that have gone past their expiry date.

        Nothing is auto-rejected: an expired estimate is often still live, and
        silently killing a deal is worse than an extra reminder.
        """
        today = fields.Date.context_today(self)
        expired = self.search([
            ('date_expiry', '<', today),
            ('state', 'in', ('draft', 'confirmed', 'approved')),
        ])
        for rec in expired:
            if rec.activity_ids.filtered(
                    lambda a: a.summary == 'Estimate expired'):
                continue
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Estimate expired'),
                note=_('This estimate passed its expiry date on %s.',
                       rec.date_expiry),
                user_id=rec.user_id.id or self.env.uid)
        return True

    @api.depends('state')
    def _compute_progress(self):
        for rec in self:
            rec.progress = rec._PROGRESS_BY_STATE.get(rec.state, 0.0)

    def _get_portal_qr_src(self):
        """Barcode-controller URL for a QR of the portal link.

        Built here rather than in QWeb so the portal URL is encoded properly -
        it contains query parameters that would otherwise break the src.
        """
        self.ensure_one()
        params = urlencode({
            'barcode_type': 'QR',
            'value': self.get_portal_url(),
            'width': 120,
            'height': 120,
        })
        return '/report/barcode/?%s' % params

    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends('origin_estimate_id', 'revision_ids')
    def _compute_revision_count(self):
        for rec in self:
            root = rec.origin_estimate_id or rec
            rec.revision_count = self.search_count([
                '|', ('origin_estimate_id', '=', root.id), ('id', '=', root.id),
            ]) - 1

    @api.depends('sale_order_id')
    def _compute_sale_count(self):
        for rec in self:
            rec.sale_count = 1 if rec.sale_order_id else 0

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/estimate/%s' % rec.id

    # ------------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inom.cost.estimate') or _('New')
        return super().create(vals_list)

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Estimate - %s' % (self.name or '')

    # ------------------------------------------------------------------
    # Actions - Workflow
    # ------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only a draft estimate can be confirmed.'))
            if not (rec.material_line_ids or rec.labour_line_ids
                    or rec.equipment_line_ids or rec.overhead_line_ids):
                raise UserError(_('Please add at least one cost line before confirming.'))
            rec.state = 'confirmed'

    def action_approve(self):
        threshold = self._get_approval_threshold()
        threshold_high = self._get_approval_threshold_high()
        is_manager = self.env.user.has_group(
            'inom_job_cost_estimation.group_inom_cost_manager')
        is_director = self.env.user.has_group(
            'inom_job_cost_estimation.group_inom_cost_director')
        for rec in self:
            if rec.state not in ('draft', 'confirmed'):
                raise UserError(_('This estimate can no longer be approved.'))
            if (threshold_high and rec.amount_total > threshold_high
                    and not is_director):
                raise UserError(_(
                    'This estimate total (%(total)s) exceeds the director '
                    'threshold (%(limit)s) and requires a Job Costing Director '
                    'to approve.',
                    total=rec.amount_total, limit=threshold_high))
            if threshold and rec.amount_total > threshold and not is_manager:
                raise UserError(_(
                    'This estimate total (%(total)s) exceeds the approval '
                    'threshold (%(limit)s) and requires a Job Costing Manager '
                    'to approve.',
                    total=rec.amount_total, limit=threshold))
            rec.state = 'approved'

    def action_open_reject_wizard(self):
        self.ensure_one()
        if self.state == 'converted':
            raise UserError(_(
                'This estimate has already been converted into quotation %s.'
            ) % self.sale_order_id.display_name)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Estimate'),
            'res_model': 'inom.cost.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_estimate_id': self.id},
        }

    def action_reject(self):
        for rec in self:
            if rec.state == 'converted':
                raise UserError(_(
                    'This estimate has already been converted into quotation '
                    '%s and cannot be rejected. Cancel the quotation first.'
                ) % rec.sale_order_id.display_name)
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        """Send an estimate back to draft.

        A converted estimate is deliberately blocked: its quotation already
        exists, so reopening it would leave two live documents claiming the
        same job. Any customer acceptance is cleared, because reopening the
        estimate invalidates what was signed for.
        """
        for rec in self:
            if rec.state == 'converted':
                raise UserError(_(
                    'This estimate is linked to quotation %s. Create a new '
                    'revision instead of resetting it to draft.'
                ) % rec.sale_order_id.display_name)
        self.write({'state': 'draft', 'signed_by': False, 'signed_on': False})

    def action_load_template(self):
        self.ensure_one()
        if not self.template_id:
            raise UserError(_('Please select a template to load.'))
        mat = [(5, 0, 0)]
        lab = [(5, 0, 0)]
        eqp = [(5, 0, 0)]
        ovh = [(5, 0, 0)]
        for tl in self.template_id.line_ids:
            if tl.line_type == 'material':
                mat.append((0, 0, {
                    'product_id': tl.product_id.id,
                    'name': tl.name,
                    'quantity': tl.quantity,
                    'uom_id': tl.uom_id.id,
                    'price_unit': tl.price_unit,
                }))
            elif tl.line_type == 'labour':
                lab.append((0, 0, {
                    'name': tl.name,
                    'job_id': tl.job_id.id,
                    'quantity': tl.quantity,
                    'hours': tl.hours,
                    'price_unit': tl.price_unit,
                }))
            elif tl.line_type == 'equipment':
                eqp.append((0, 0, {
                    'product_id': tl.product_id.id,
                    'name': tl.name,
                    'quantity': tl.quantity,
                    'duration': tl.hours or 1.0,
                    'price_unit': tl.price_unit,
                }))
            else:
                ovh.append((0, 0, {'name': tl.name, 'amount': tl.amount}))
        self.write({
            'material_line_ids': mat,
            'labour_line_ids': lab,
            'equipment_line_ids': eqp,
            'overhead_line_ids': ovh,
        })

    def action_create_revision(self):
        self.ensure_one()
        root = self.origin_estimate_id or self
        new_rev = self.copy({
            'origin_estimate_id': root.id,
            'revision': self.revision + 1,
            'state': 'draft',
            'name': _('New'),
            'sale_order_id': False,
            'signed_by': False,
            'signed_on': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Estimate Revision'),
            'res_model': 'inom.cost.estimate',
            'res_id': new_rev.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Conversion to quotation
    # ------------------------------------------------------------------
    def _get_markup_factor(self):
        """Default ratio for lines that do not override the markup themselves."""
        self.ensure_one()
        return 1.0 + (self.markup_percent or 0.0) / 100.0

    def _get_conversion_product(self, kind):
        """Return the fallback service product for ``kind``.

        ``kind`` is one of ``material``, ``labour``, ``equipment`` or
        ``overhead``. A product
        configured in Settings wins over the module default.
        """
        self.ensure_one()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'inom_job_cost_estimation.%s_product_id' % kind)
        if param:
            product = self.env['product.product'].browse(int(param)).exists()
            if product:
                return product
        default_ref = {
            'material': 'inom_job_cost_estimation.product_inom_material_generic',
            'labour': 'inom_job_cost_estimation.product_inom_labour',
            'equipment': 'inom_job_cost_estimation.product_inom_equipment',
            'overhead': 'inom_job_cost_estimation.product_inom_overhead',
        }[kind]
        product = self.env.ref(default_ref, raise_if_not_found=False)
        if not product:
            raise UserError(_(
                'No product is configured for %(kind)s lines. Please set one '
                'in Settings > Job Costing before converting this estimate.',
                kind=kind))
        return product

    def _get_order_currency(self):
        """Currency the quotation will end up in.

        The order takes its currency from the customer's pricelist, so that is
        what the converted amounts have to be expressed in. The field holding
        the pricelist has been renamed between versions, so both names are
        probed before falling back to the company currency.
        """
        self.ensure_one()
        partner = self.partner_id.with_company(self.company_id)
        for fname in ('property_product_pricelist', 'pricelist_id'):
            if fname in partner._fields and partner[fname]:
                return partner[fname].currency_id
        return self.company_id.currency_id or self.currency_id

    def _convert_price(self, amount, target):
        self.ensure_one()
        if not target or target == self.currency_id:
            return amount
        return self.currency_id._convert(
            amount, target, self.company_id,
            self.date_estimate or fields.Date.context_today(self))

    def _prepare_sale_order_line_vals(self, product, name, qty, price_unit,
                                      sequence, discount=0.0):
        self.ensure_one()
        # sale.order.line renamed tax_id to tax_ids in Odoo 19; probe the
        # model so the same code works on 17, 18 and 19.
        SaleLine = self.env['sale.order.line']
        tax_field = 'tax_ids' if 'tax_ids' in SaleLine._fields else 'tax_id'
        price_unit = self._convert_price(price_unit, self._get_order_currency())
        vals = {
            'sequence': sequence,
            'product_id': product.id,
            'name': name,
            'product_uom_qty': qty,
            'price_unit': price_unit,
            tax_field: [(6, 0, self.tax_ids.ids)],
        }
        if discount:
            vals['discount'] = discount
        if self.analytic_account_id:
            vals['analytic_distribution'] = {str(self.analytic_account_id.id): 100.0}
        return vals

    def _prepare_sale_order_lines(self):
        """Build order lines that carry the full estimate value.

        Material, manpower, equipment and indirect costs all become priced
        lines at the
        marked-up selling rate, so the quotation total matches the estimate
        total instead of only reflecting material.
        """
        self.ensure_one()
        lines = []
        seq = 10

        if self.material_line_ids:
            lines.append((0, 0, {'sequence': seq, 'display_type': 'line_section',
                                 'name': _('Materials')}))
            seq += 10
            fallback = None
            for line in self.material_line_ids:
                factor = line._get_markup_factor()
                if line.product_id:
                    product = line.product_id
                    qty = line.quantity
                    price = line.price_unit * factor
                else:
                    fallback = fallback or self._get_conversion_product('material')
                    product = fallback
                    qty = 1.0
                    price = line.price_subtotal * factor
                lines.append((0, 0, self._prepare_sale_order_line_vals(
                    product, line.name or product.display_name, qty, price, seq,
                    line._get_effective_discount())))
                seq += 10

        if self.labour_line_ids:
            product = self._get_conversion_product('labour')
            lines.append((0, 0, {'sequence': seq, 'display_type': 'line_section',
                                 'name': _('Manpower')}))
            seq += 10
            for line in self.labour_line_ids:
                factor = line._get_markup_factor()
                qty = (line.quantity or 0.0) * (line.hours or 0.0)
                if qty:
                    price = line.price_unit * factor
                else:
                    qty, price = 1.0, line.price_subtotal * factor
                lines.append((0, 0, self._prepare_sale_order_line_vals(
                    product, line.name, qty, price, seq,
                    line._get_effective_discount())))
                seq += 10

        if self.equipment_line_ids:
            product = self._get_conversion_product('equipment')
            lines.append((0, 0, {'sequence': seq, 'display_type': 'line_section',
                                 'name': _('Equipment')}))
            seq += 10
            for line in self.equipment_line_ids:
                factor = line._get_markup_factor()
                qty = (line.quantity or 0.0) * (line.duration or 0.0)
                if qty:
                    price = line.price_unit * factor
                else:
                    qty, price = 1.0, line.price_subtotal * factor
                lines.append((0, 0, self._prepare_sale_order_line_vals(
                    product, line.name, qty, price, seq,
                    line._get_effective_discount())))
                seq += 10

        if self.overhead_line_ids:
            product = self._get_conversion_product('overhead')
            lines.append((0, 0, {'sequence': seq, 'display_type': 'line_section',
                                 'name': _('Indirect Cost')}))
            seq += 10
            for line in self.overhead_line_ids:
                lines.append((0, 0, self._prepare_sale_order_line_vals(
                    product, line.name, 1.0,
                    line.amount * line._get_markup_factor(), seq,
                    line._get_effective_discount())))
                seq += 10

        if self.amount_rounding:
            # The estimate rounds the tax-inclusive total, so the quotation
            # needs the same adjustment as an untaxed line - otherwise the two
            # documents disagree by the rounding amount.
            SaleLine = self.env['sale.order.line']
            tax_field = 'tax_ids' if 'tax_ids' in SaleLine._fields else 'tax_id'
            product = self._get_conversion_product('overhead')
            lines.append((0, 0, {
                'sequence': seq,
                'product_id': product.id,
                'name': _('Rounding'),
                'product_uom_qty': 1.0,
                'price_unit': self._convert_price(
                    self.amount_rounding, self._get_order_currency()),
                tax_field: [(6, 0, [])],
            }))

        return lines

    def _prepare_sale_order_vals(self):
        self.ensure_one()
        return {
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'client_order_ref': self.reference or False,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id or False,
            'inom_estimate_id': self.id,
            'order_line': self._prepare_sale_order_lines(),
        }

    def action_convert_to_quotation(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved estimates can be converted to a quotation.'))
        if self.sale_order_id:
            raise UserError(_('This estimate is already linked to a quotation.'))
        if not (self.material_line_ids or self.labour_line_ids
                or self.equipment_line_ids or self.overhead_line_ids):
            raise UserError(_('This estimate has no cost lines to convert.'))
        expected = self._get_order_currency()
        order = self.env['sale.order'].create(self._prepare_sale_order_vals())
        # Line prices were converted into `expected`. If the order actually
        # settled on a different currency, the figures on it are wrong, so
        # stop instead of leaving a mispriced quotation behind - raising rolls
        # the whole thing back, order included.
        if order.currency_id != expected:
            raise UserError(_(
                'This estimate is in %(est)s and its amounts were converted to '
                '%(exp)s, but the quotation was created in %(ord)s. Set a '
                'pricelist in %(est)s on the customer, or change the estimate '
                'currency, before converting.',
                est=self.currency_id.name, exp=expected.name,
                ord=order.currency_id.name))
        self.write({'sale_order_id': order.id, 'state': 'converted'})
        self.message_post(body=_(
            'Converted into quotation %(order)s.', order=order.name))
        if order.currency_id != self.currency_id:
            self.message_post(body=_(
                'Amounts converted from %(est)s to %(ord)s at the rate of '
                '%(date)s.',
                est=self.currency_id.name, ord=order.currency_id.name,
                date=self.date_estimate or fields.Date.context_today(self)))
        return self.action_view_sale_order()

    def action_send_email(self):
        self.ensure_one()
        template = self.env.ref(
            'inom_job_cost_estimation.mail_template_estimate',
            raise_if_not_found=False)
        ctx = {
            'default_model': 'inom.cost.estimate',
            'default_res_ids': self.ids,
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Estimate by Email'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': ctx,
        }

    # ------------------------------------------------------------------
    # Actions - Navigation
    # ------------------------------------------------------------------
    def action_create_analytic_account(self):
        """Create and attach an analytic account named after the estimate."""
        self.ensure_one()
        if self.analytic_account_id:
            raise UserError(_('An analytic account is already linked.'))
        plan = self.env['account.analytic.plan'].sudo().search(
            [('parent_id', '=', False)], limit=1)
        if not plan:
            raise UserError(_(
                'No analytic plan is configured. Please create one in '
                'Accounting before generating an analytic account.'))
        self.analytic_account_id = self.env['account.analytic.account'].create({
            'name': '%s - %s' % (self.name, self.partner_id.display_name),
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'plan_id': plan.id,
        })

    def action_view_analytic_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Analytic Items'),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form',
            'domain': [('account_id', '=', self.analytic_account_id.id)],
            'context': {'default_account_id': self.analytic_account_id.id},
        }

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quotation'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.document_ids.ids)],
            'context': {'create': False},
        }

    def action_view_revisions(self):
        self.ensure_one()
        root = self.origin_estimate_id or self
        return {
            'type': 'ir.actions.act_window',
            'name': _('Revisions'),
            'res_model': 'inom.cost.estimate',
            'view_mode': 'list,form',
            'domain': ['|', ('origin_estimate_id', '=', root.id), ('id', '=', root.id)],
        }

    # ------------------------------------------------------------------
    # Portal helper
    # ------------------------------------------------------------------
    def _get_approval_threshold(self):
        return float(self.env['ir.config_parameter'].sudo().get_param(
            'inom_job_cost_estimation.approval_threshold', 0.0) or 0.0)

    def _get_approval_threshold_high(self):
        return float(self.env['ir.config_parameter'].sudo().get_param(
            'inom_job_cost_estimation.approval_threshold_high', 0.0) or 0.0)

    def _portal_sign(self, signer_name, signature=None):
        """Record a customer's online acceptance.

        The customer signature never bypasses the internal approval threshold:
        above the threshold the estimate only moves to ``confirmed`` and still
        needs a Job Costing Manager to approve it.
        """
        self.ensure_one()
        vals = {
            'signed_by': signer_name,
            'signed_on': fields.Datetime.now(),
        }
        if signature:
            vals['signature'] = signature
        threshold = self._get_approval_threshold()
        threshold_high = self._get_approval_threshold_high()
        over_threshold = ((bool(threshold) and self.amount_total > threshold)
                          or (bool(threshold_high) and self.amount_total > threshold_high))
        if self.state in ('draft', 'confirmed'):
            vals['state'] = 'confirmed' if over_threshold else 'approved'
        self.sudo().write(vals)
        if over_threshold:
            body = _(
                'Estimate accepted online by %(signer)s. The total exceeds the '
                'approval threshold, so internal approval by a Job Costing '
                'Manager is still required.', signer=signer_name)
        else:
            body = _('Estimate approved online by %(signer)s.', signer=signer_name)
        self.sudo().message_post(body=body)
        if over_threshold:
            self.sudo().activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=(self.user_id or self.env.user).id,
                summary=_('Customer accepted - manager approval required'))
