# -*- coding: utf-8 -*-
import secrets
from urllib.parse import quote

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomAsset(models.Model):
    _name = 'inom.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reference_no desc'

    name = fields.Char(
        string='Asset Name', required=True, tracking=True, translate=True)
    reference_no = fields.Char(
        string='Asset Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'))
    image_1920 = fields.Image(string='Image')
    category_id = fields.Many2one(
        'inom.asset.category', string='Category',
        required=True, tracking=True)
    location_id = fields.Many2one(
        'inom.asset.location', string='Current Location', tracking=True)
    parent_id = fields.Many2one(
        'inom.asset', string='Parent Asset', index=True, tracking=True)
    child_ids = fields.One2many(
        'inom.asset', 'parent_id', string='Component Assets')
    child_count = fields.Integer(compute='_compute_child_count')
    assigned_employee_id = fields.Many2one(
        'hr.employee', string='Custodian', tracking=True)
    department_id = fields.Many2one(
        'hr.department', string='Department',
        related='assigned_employee_id.department_id', store=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        related='company_id.currency_id', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_use', 'In Use'),
        ('in_store', 'In Store'),
        ('under_maintenance', 'Under Maintenance'),
        ('scrapped', 'Scrapped'),
    ], string='Status', default='draft', required=True, tracking=True)
    criticality = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Criticality', default='medium', tracking=True)

    # Technical identity
    serial_no = fields.Char(string='Serial Number', copy=False)
    model_no = fields.Char(string='Model Number')
    manufacturer_id = fields.Many2one('res.partner', string='Manufacturer')
    product_id = fields.Many2one(
        'product.product', string='Related Product',
        help='Optional link to the product used when purchasing spare '
             'units of this asset.')

    # Procurement / financial
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    purchase_date = fields.Date(string='Purchase Date')
    commissioning_date = fields.Date(string='Commissioning Date')
    purchase_value = fields.Monetary(
        string='Purchase Value', currency_field='currency_id')
    salvage_value = fields.Monetary(
        string='Salvage Value', currency_field='currency_id')
    warranty_expiry_date = fields.Date(string='Warranty Expiry', tracking=True)
    warranty_state = fields.Selection([
        ('none', 'No Warranty'),
        ('valid', 'Under Warranty'),
        ('expired', 'Warranty Expired'),
    ], string='Warranty Status', compute='_compute_warranty_state')

    # Depreciation
    enable_depreciation = fields.Boolean(string='Enable Depreciation')
    depreciation_method = fields.Selection([
        ('linear', 'Straight Line'),
        ('declining', 'Declining Balance'),
    ], string='Depreciation Method', default='linear')
    depreciation_years = fields.Integer(string='Asset Life (Years)', default=5)
    declining_factor = fields.Float(string='Declining Factor', default=2.0)
    depreciation_start_date = fields.Date(string='Depreciation Start Date')
    depreciation_line_ids = fields.One2many(
        'inom.asset.depreciation.line', 'asset_id',
        string='Depreciation Schedule')
    accumulated_depreciation = fields.Monetary(
        string='Accumulated Depreciation',
        compute='_compute_book_value', currency_field='currency_id')
    book_value = fields.Monetary(
        string='Current Book Value',
        compute='_compute_book_value', currency_field='currency_id')

    # Relations
    transfer_ids = fields.One2many(
        'inom.asset.transfer', 'asset_id', string='Transfers')
    transfer_count = fields.Integer(compute='_compute_counts')
    maintenance_request_ids = fields.One2many(
        'inom.maintenance.request', 'asset_id', string='Maintenance Requests')
    maintenance_request_count = fields.Integer(compute='_compute_counts')
    work_order_ids = fields.One2many(
        'inom.work.order', 'asset_id', string='Work Orders')
    work_order_count = fields.Integer(compute='_compute_counts')
    inspection_ids = fields.One2many(
        'inom.asset.inspection', 'asset_id', string='Inspections')
    inspection_count = fields.Integer(compute='_compute_counts')
    meter_ids = fields.One2many(
        'inom.asset.meter', 'asset_id', string='Meters')
    meter_count = fields.Integer(compute='_compute_counts')
    plan_ids = fields.One2many(
        'inom.maintenance.plan', 'asset_id', string='Maintenance Plans')

    # Analytics
    mtbf_days = fields.Float(
        string='MTBF (Days)', compute='_compute_reliability_kpi',
        help='Mean Time Between Failures computed from closed corrective '
             'work orders.')
    mttr_hours = fields.Float(
        string='MTTR (Hours)', compute='_compute_reliability_kpi',
        help='Mean Time To Repair computed from closed work orders.')
    health_score = fields.Integer(
        string='Health Score', compute='_compute_health_score',
        help='Composite score (0-100) based on failures, age and '
             'open maintenance load.')
    total_maintenance_cost = fields.Monetary(
        string='Total Maintenance Cost', currency_field='currency_id',
        compute='_compute_reliability_kpi')

    # IoT
    iot_token = fields.Char(
        string='IoT Access Token', copy=False, groups='inom_asset_care.group_asset_manager')
    note = fields.Html(string='Internal Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('serial_company_uniq', 'unique(serial_no, company_id)',
         'Serial number must be unique per company.'),
    ]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference_no', _('New')) == _('New'):
                vals['reference_no'] = self.env['ir.sequence'].next_by_code(
                    'inom.asset') or _('New')
        return super().create(vals_list)

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if self._has_cycle():
            raise UserError(_('You cannot create a recursive asset hierarchy.'))

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            self.depreciation_method = self.category_id.depreciation_method
            self.depreciation_years = self.category_id.depreciation_years
            self.declining_factor = self.category_id.declining_factor

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    def _compute_child_count(self):
        for asset in self:
            asset.child_count = len(asset.child_ids)

    def _compute_counts(self):
        for asset in self:
            asset.transfer_count = len(asset.transfer_ids)
            asset.maintenance_request_count = len(asset.maintenance_request_ids)
            asset.work_order_count = len(asset.work_order_ids)
            asset.inspection_count = len(asset.inspection_ids)
            asset.meter_count = len(asset.meter_ids)

    @api.depends('warranty_expiry_date')
    def _compute_warranty_state(self):
        today = fields.Date.context_today(self)
        for asset in self:
            if not asset.warranty_expiry_date:
                asset.warranty_state = 'none'
            elif asset.warranty_expiry_date >= today:
                asset.warranty_state = 'valid'
            else:
                asset.warranty_state = 'expired'

    @api.depends('depreciation_line_ids.state',
                 'depreciation_line_ids.amount', 'purchase_value')
    def _compute_book_value(self):
        for asset in self:
            posted = asset.depreciation_line_ids.filtered(
                lambda l: l.state == 'posted')
            asset.accumulated_depreciation = sum(posted.mapped('amount'))
            asset.book_value = (asset.purchase_value or 0.0) - \
                asset.accumulated_depreciation

    def _compute_reliability_kpi(self):
        for asset in self:
            closed_wo = asset.work_order_ids.filtered(
                lambda w: w.state in ('done', 'closed'))
            corrective = closed_wo.filtered(
                lambda w: w.wo_type == 'corrective' and w.actual_start_date)
            # MTBF: average gap between consecutive corrective failures
            mtbf = 0.0
            if len(corrective) > 1:
                dates = sorted(corrective.mapped('actual_start_date'))
                gaps = [
                    (dates[i + 1] - dates[i]).total_seconds() / 86400.0
                    for i in range(len(dates) - 1)
                ]
                mtbf = sum(gaps) / len(gaps)
            asset.mtbf_days = mtbf
            # MTTR: average repair duration on closed work orders
            durations = [
                w.actual_duration for w in closed_wo if w.actual_duration
            ]
            asset.mttr_hours = (
                sum(durations) / len(durations)) if durations else 0.0
            asset.total_maintenance_cost = sum(closed_wo.mapped('total_cost'))

    def _compute_health_score(self):
        today = fields.Date.context_today(self)
        for asset in self:
            score = 100
            open_requests = asset.maintenance_request_ids.filtered(
                lambda r: r.state not in ('done', 'cancelled'))
            score -= min(len(open_requests) * 10, 40)
            corrective_wo = asset.work_order_ids.filtered(
                lambda w: w.wo_type == 'corrective')
            score -= min(len(corrective_wo) * 3, 30)
            if asset.warranty_state == 'expired':
                score -= 5
            if asset.commissioning_date:
                age_years = (today - asset.commissioning_date).days / 365.0
                life = asset.depreciation_years or 5
                if age_years > life:
                    score -= 15
                elif age_years > life * 0.7:
                    score -= 7
            asset.health_score = max(score, 0)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_set_in_use(self):
        self.write({'state': 'in_use'})

    def action_set_in_store(self):
        self.write({'state': 'in_store'})

    def action_scrap(self):
        for asset in self:
            open_wo = asset.work_order_ids.filtered(
                lambda w: w.state not in ('done', 'closed', 'cancelled'))
            if open_wo:
                raise UserError(_(
                    'Asset %s still has open work orders. Close them before '
                    'scrapping.', asset.display_name))
        self.write({'state': 'scrapped', 'active': True})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_generate_iot_token(self):
        for asset in self:
            asset.iot_token = secrets.token_urlsafe(24)

    def action_compute_depreciation_schedule(self):
        self.ensure_one()
        if not self.enable_depreciation:
            raise UserError(_('Enable depreciation on this asset first.'))
        if not self.purchase_value or not self.depreciation_start_date:
            raise UserError(_(
                'Purchase value and depreciation start date are required to '
                'compute the schedule.'))
        self.env['inom.asset.depreciation.line'].generate_schedule(self)
        return True

    def action_send_whatsapp(self):
        """Open a WhatsApp deep link with the asset summary for the
        custodian of the asset."""
        self.ensure_one()
        message = _(
            'Asset Update\nReference: %(ref)s\nName: %(name)s\n'
            'Status: %(state)s\nLocation: %(location)s',
            ref=self.reference_no, name=self.name,
            state=dict(self._fields['state'].selection).get(self.state),
            location=self.location_id.complete_name or '-')
        return self._open_whatsapp_link(
            self.assigned_employee_id.mobile_phone
            or self.assigned_employee_id.work_phone, message)

    def _open_whatsapp_link(self, phone, message):
        if not self.env.company.inom_whatsapp_enabled:
            raise UserError(_(
                'WhatsApp notifications are disabled. Enable them from '
                'Settings > AssetCare.'))
        if not phone:
            raise UserError(_('No mobile number found for the recipient.'))
        number = ''.join(ch for ch in phone if ch.isdigit())
        prefix = self.env.company.inom_whatsapp_country_code or ''
        if prefix and not phone.strip().startswith('+') \
                and len(number) <= 10:
            number = ''.join(ch for ch in prefix if ch.isdigit()) + number
        url = 'https://wa.me/%s?text=%s' % (number, quote(message))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_view_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Component Assets'),
            'res_model': 'inom.asset',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id},
        }

    def _get_smart_action(self, model, name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_view_transfers(self):
        return self._get_smart_action('inom.asset.transfer', _('Transfers'))

    def action_view_requests(self):
        return self._get_smart_action(
            'inom.maintenance.request', _('Maintenance Requests'))

    def action_view_work_orders(self):
        return self._get_smart_action('inom.work.order', _('Work Orders'))

    def action_view_inspections(self):
        return self._get_smart_action(
            'inom.asset.inspection', _('Inspections'))

    def action_view_meters(self):
        return self._get_smart_action('inom.asset.meter', _('Meters'))

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_warranty_expiry_alert(self):
        """Create an activity for the asset manager when warranty is about
        to expire within 30 days."""
        today = fields.Date.context_today(self)
        limit = fields.Date.add(today, days=30)
        assets = self.search([
            ('warranty_expiry_date', '!=', False),
            ('warranty_expiry_date', '>=', today),
            ('warranty_expiry_date', '<=', limit),
            ('state', '!=', 'scrapped'),
        ])
        activity_type = self.env.ref(
            'mail.mail_activity_data_todo', raise_if_not_found=False)
        for asset in assets:
            existing = asset.activity_ids.filtered(
                lambda a: a.summary and 'Warranty expiring' in a.summary)
            if existing:
                continue
            asset.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('Warranty expiring soon'),
                note=_('Warranty of asset %s expires on %s.',
                       asset.display_name, asset.warranty_expiry_date),
                date_deadline=asset.warranty_expiry_date,
                user_id=self.env.ref('base.user_admin').id,
            )
