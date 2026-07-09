# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomWorkOrder(models.Model):
    _name = 'inom.work.order'
    _description = 'Maintenance Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'planned_start_date desc, id desc'

    name = fields.Char(
        string='Work Order Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'))
    title = fields.Char(string='Work Summary', required=True, tracking=True)
    request_id = fields.Many2one(
        'inom.maintenance.request', string='Maintenance Request',
        ondelete='set null')
    asset_id = fields.Many2one(
        'inom.asset', string='Asset', required=True, tracking=True)
    location_id = fields.Many2one(
        related='asset_id.location_id', store=True)
    wo_type = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Preventive'),
        ('inspection', 'Inspection'),
        ('improvement', 'Improvement'),
    ], string='Work Order Type', default='corrective', required=True,
        tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1', tracking=True)
    team_id = fields.Many2one('inom.maintenance.team', string='Team')
    technician_ids = fields.Many2many(
        'hr.employee', 'inom_wo_technician_rel', 'wo_id', 'employee_id',
        string='Technicians')
    supervisor_id = fields.Many2one('res.users', string='Supervisor')
    planned_start_date = fields.Datetime(string='Planned Start')
    planned_end_date = fields.Datetime(string='Planned End')
    actual_start_date = fields.Datetime(string='Actual Start', readonly=True)
    actual_end_date = fields.Datetime(string='Actual End', readonly=True)
    actual_duration = fields.Float(
        string='Actual Duration (Hours)',
        compute='_compute_actual_duration', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('in_progress', 'In Progress'),
        ('paused', 'On Hold'),
        ('done', 'Done'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    instruction = fields.Html(string='Work Instructions')

    # Safety
    permit_required = fields.Boolean(string='Safety Permit Required')
    permit_ids = fields.One2many(
        'inom.work.permit', 'work_order_id', string='Safety Permits')
    permit_count = fields.Integer(compute='_compute_permit_count')

    # Cost lines
    labor_line_ids = fields.One2many(
        'inom.work.order.labor', 'work_order_id', string='Labor Lines')
    part_line_ids = fields.One2many(
        'inom.work.order.part', 'work_order_id', string='Spare Part Lines')
    checklist_line_ids = fields.One2many(
        'inom.work.order.checklist', 'work_order_id',
        string='Checklist Items')
    checklist_progress = fields.Float(
        string='Checklist Progress', compute='_compute_checklist_progress')
    labor_cost = fields.Monetary(
        string='Labor Cost', compute='_compute_costs', store=True,
        currency_field='currency_id')
    part_cost = fields.Monetary(
        string='Parts Cost', compute='_compute_costs', store=True,
        currency_field='currency_id')
    total_cost = fields.Monetary(
        string='Total Cost', compute='_compute_costs', store=True,
        currency_field='currency_id')

    # Failure analysis
    failure_code = fields.Selection([
        ('mechanical', 'Mechanical Failure'),
        ('electrical', 'Electrical Failure'),
        ('operator', 'Operator Error'),
        ('wear', 'Normal Wear & Tear'),
        ('external', 'External Damage'),
        ('other', 'Other'),
    ], string='Failure Code')
    root_cause = fields.Text(string='Root Cause Analysis')
    corrective_action = fields.Text(string='Action Taken')

    source_warehouse_id = fields.Many2one(
        'stock.location', string='Parts Source Location',
        domain="[('usage', '=', 'internal')]")
    picking_id = fields.Many2one(
        'stock.picking', string='Parts Consumption Transfer', readonly=True,
        copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inom.work.order') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    def _compute_permit_count(self):
        for order in self:
            order.permit_count = len(order.permit_ids)

    @api.depends('actual_start_date', 'actual_end_date')
    def _compute_actual_duration(self):
        for order in self:
            if order.actual_start_date and order.actual_end_date:
                delta = order.actual_end_date - order.actual_start_date
                order.actual_duration = delta.total_seconds() / 3600.0
            else:
                order.actual_duration = 0.0

    def _compute_checklist_progress(self):
        for order in self:
            total = len(order.checklist_line_ids)
            done = len(order.checklist_line_ids.filtered('is_done'))
            order.checklist_progress = (done / total * 100.0) if total else 0.0

    @api.depends('labor_line_ids.cost_subtotal',
                 'part_line_ids.cost_subtotal')
    def _compute_costs(self):
        for order in self:
            order.labor_cost = sum(
                order.labor_line_ids.mapped('cost_subtotal'))
            order.part_cost = sum(
                order.part_line_ids.mapped('cost_subtotal'))
            order.total_cost = order.labor_cost + order.part_cost

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_ready(self):
        self.write({'state': 'ready'})

    def action_start(self):
        for order in self:
            if order.permit_required:
                valid_permits = order.permit_ids.filtered(
                    lambda p: p.state in ('approved', 'active'))
                if not valid_permits:
                    raise UserError(_(
                        'Work order %s requires an approved safety permit '
                        'before work can start.', order.name))
            order.write({
                'state': 'in_progress',
                'actual_start_date': order.actual_start_date
                or fields.Datetime.now(),
            })
            if order.asset_id.state == 'in_use':
                order.asset_id.state = 'under_maintenance'

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_resume(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        for order in self:
            pending = order.checklist_line_ids.filtered(
                lambda l: l.is_mandatory and not l.is_done)
            if pending:
                raise UserError(_(
                    'Mandatory checklist items are still pending on %s.',
                    order.name))
            order.write({
                'state': 'done',
                'actual_end_date': fields.Datetime.now(),
            })
            if order.asset_id.state == 'under_maintenance':
                order.asset_id.state = 'in_use'

    def action_close(self):
        for order in self:
            if order.part_line_ids and not order.picking_id:
                order._create_parts_consumption()
            active_permits = order.permit_ids.filtered(
                lambda p: p.state == 'active')
            active_permits.action_close()
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Stock integration
    # ------------------------------------------------------------------
    def _create_parts_consumption(self):
        """Consume spare parts through a real internal transfer so that
        inventory valuation stays accurate."""
        self.ensure_one()
        if not self.source_warehouse_id:
            raise UserError(_(
                'Set a parts source location on %s before closing.',
                self.name))
        consumable_lines = self.part_line_ids.filtered(
            lambda l: l.product_id.is_storable and l.quantity > 0)
        if not consumable_lines:
            return
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'internal'),
             ('company_id', 'in', (self.company_id.id, False))],
            limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search(
                [('code', 'in', ('outgoing', 'internal')),
                 ('company_id', 'in', (self.company_id.id, False))],
                limit=1)
        if not picking_type:
            raise UserError(_(
                'No stock operation type found for this company. '
                'Please configure a warehouse first.'))
        scrap_dest = self.env['stock.location'].search(
            [('usage', '=', 'inventory'),
             ('company_id', 'in', (self.company_id.id, False))], limit=1)
        if not scrap_dest:
            scrap_dest = picking_type.default_location_dest_id
        if not scrap_dest:
            scrap_dest = picking_type.default_location_dest_id
        if not scrap_dest:
            raise UserError(_(
                'No consumption location found for this company.'))
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.source_warehouse_id.id,
            'location_dest_id': scrap_dest.id,
            'origin': self.name,
            'move_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'location_id': self.source_warehouse_id.id,
                'location_dest_id': scrap_dest.id,
            }) for line in consumable_lines],
        })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.button_validate()
        self.picking_id = picking

    def action_notify_whatsapp(self):
        self.ensure_one()
        technician = self.technician_ids[:1]
        message = _(
            'Work Order %(ref)s\nAsset: %(asset)s\nWork: %(title)s\n'
            'Planned Start: %(start)s\nPriority: %(priority)s',
            ref=self.name, asset=self.asset_id.display_name,
            title=self.title,
            start=fields.Datetime.to_string(self.planned_start_date) or '-',
            priority=dict(
                self._fields['priority'].selection).get(self.priority))
        phone = technician.mobile_phone or technician.work_phone
        return self.asset_id._open_whatsapp_link(phone, message)


class InomWorkOrderLabor(models.Model):
    _name = 'inom.work.order.labor'
    _description = 'Work Order Labor Line'

    work_order_id = fields.Many2one(
        'inom.work.order', string='Work Order', required=True,
        ondelete='cascade')
    employee_id = fields.Many2one(
        'hr.employee', string='Technician', required=True)
    work_date = fields.Date(
        string='Date', default=fields.Date.context_today)
    hours_spent = fields.Float(string='Hours Spent', default=1.0)
    hourly_rate = fields.Float(string='Hourly Rate')
    cost_subtotal = fields.Monetary(
        string='Cost', compute='_compute_cost_subtotal', store=True,
        currency_field='currency_id')
    currency_id = fields.Many2one(
        related='work_order_id.currency_id')
    remarks = fields.Char(string='Remarks')

    @api.depends('hours_spent', 'hourly_rate')
    def _compute_cost_subtotal(self):
        for line in self:
            line.cost_subtotal = line.hours_spent * line.hourly_rate


class InomWorkOrderPart(models.Model):
    _name = 'inom.work.order.part'
    _description = 'Work Order Spare Part Line'

    work_order_id = fields.Many2one(
        'inom.work.order', string='Work Order', required=True,
        ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Spare Part', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_cost = fields.Float(
        string='Unit Cost', compute='_compute_unit_cost',
        store=True, readonly=False)
    cost_subtotal = fields.Monetary(
        string='Cost', compute='_compute_cost_subtotal', store=True,
        currency_field='currency_id')
    currency_id = fields.Many2one(related='work_order_id.currency_id')

    @api.depends('product_id')
    def _compute_unit_cost(self):
        for line in self:
            line.unit_cost = line.product_id.standard_price

    @api.depends('quantity', 'unit_cost')
    def _compute_cost_subtotal(self):
        for line in self:
            line.cost_subtotal = line.quantity * line.unit_cost


class InomWorkOrderChecklist(models.Model):
    _name = 'inom.work.order.checklist'
    _description = 'Work Order Checklist Item'
    _order = 'sequence, id'

    work_order_id = fields.Many2one(
        'inom.work.order', string='Work Order', required=True,
        ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Task Description', required=True)
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    is_done = fields.Boolean(string='Completed')
    done_by_id = fields.Many2one('res.users', string='Completed By')
    remarks = fields.Char(string='Remarks')

    def write(self, vals):
        if vals.get('is_done'):
            vals.setdefault('done_by_id', self.env.user.id)
        return super().write(vals)


class InomMaintenanceTeam(models.Model):
    _name = 'inom.maintenance.team'
    _description = 'Maintenance Team'

    name = fields.Char(string='Team Name', required=True)
    leader_id = fields.Many2one('hr.employee', string='Team Leader')
    member_ids = fields.Many2many(
        'hr.employee', 'inom_team_member_rel', 'team_id', 'employee_id',
        string='Members')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)
