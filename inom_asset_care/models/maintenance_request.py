# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InomMaintenanceRequest(models.Model):
    _name = 'inom.maintenance.request'
    _description = 'Maintenance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, request_date desc'

    name = fields.Char(
        string='Request Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'))
    title = fields.Char(string='Subject', required=True, tracking=True)
    asset_id = fields.Many2one(
        'inom.asset', string='Asset', required=True, tracking=True)
    location_id = fields.Many2one(
        related='asset_id.location_id', store=True)
    request_type = fields.Selection([
        ('corrective', 'Corrective (Breakdown)'),
        ('preventive', 'Preventive'),
        ('inspection', 'Inspection Follow-up'),
        ('improvement', 'Improvement'),
    ], string='Request Type', default='corrective', required=True,
        tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1', tracking=True)
    description = fields.Html(string='Problem Description')
    requested_by_id = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user, readonly=True)
    request_date = fields.Datetime(
        string='Requested On', default=fields.Datetime.now, readonly=True)
    state = fields.Selection([
        ('new', 'New'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='new', tracking=True)
    work_order_ids = fields.One2many(
        'inom.work.order', 'request_id', string='Work Orders')
    work_order_count = fields.Integer(compute='_compute_work_order_count')
    plan_id = fields.Many2one(
        'inom.maintenance.plan', string='Source Plan', readonly=True)
    downtime_expected = fields.Boolean(string='Downtime Expected')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inom.maintenance.request') or _('New')
        return super().create(vals_list)

    def _compute_work_order_count(self):
        for request in self:
            request.work_order_count = len(request.work_order_ids)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_create_work_order(self):
        self.ensure_one()
        if self.state not in ('approved', 'in_progress'):
            raise UserError(_(
                'Request must be approved before creating a work order.'))
        work_order = self.env['inom.work.order'].create({
            'request_id': self.id,
            'asset_id': self.asset_id.id,
            'wo_type': 'preventive'
            if self.request_type == 'preventive' else 'corrective',
            'title': self.title,
            'priority': self.priority,
        })
        self.state = 'in_progress'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Order'),
            'res_model': 'inom.work.order',
            'res_id': work_order.id,
            'view_mode': 'form',
        }

    def action_mark_done(self):
        for request in self:
            open_wo = request.work_order_ids.filtered(
                lambda w: w.state not in ('done', 'closed', 'cancelled'))
            if open_wo:
                raise UserError(_(
                    'All work orders must be closed before marking request '
                    '%s as done.', request.name))
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'new'})

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'inom.work.order',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {
                'default_request_id': self.id,
                'default_asset_id': self.asset_id.id,
            },
        }
