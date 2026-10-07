# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class InomMaintenancePlan(models.Model):
    _name = 'inom.maintenance.plan'
    _description = 'Preventive Maintenance Plan'
    _inherit = ['mail.thread']

    name = fields.Char(string='Plan Name', required=True, tracking=True)
    asset_id = fields.Many2one(
        'inom.asset', string='Asset', required=True, tracking=True)
    trigger_type = fields.Selection([
        ('time', 'Time Based'),
        ('meter', 'Meter Based'),
    ], string='Trigger Type', default='time', required=True)
    # Time based
    interval_number = fields.Integer(string='Repeat Every', default=1)
    interval_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Interval Unit', default='months')
    next_due_date = fields.Date(string='Next Due Date')
    lead_days = fields.Integer(
        string='Create Request Before (Days)', default=7,
        help='The maintenance request is created this many days before the '
             'due date.')
    # Meter based
    meter_id = fields.Many2one(
        'inom.asset.meter', string='Trigger Meter',
        domain="[('asset_id', '=', asset_id), ('meter_type', '=', 'cumulative')]")
    meter_interval = fields.Float(
        string='Every (Meter Units)',
        help='A maintenance request is generated every time the meter '
             'advances by this amount.')
    last_triggered_value = fields.Float(
        string='Last Triggered At', readonly=True)

    work_summary = fields.Char(string='Work Summary')
    instruction = fields.Html(string='Standard Instructions')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1')
    request_ids = fields.One2many(
        'inom.maintenance.request', 'plan_id', string='Generated Requests')
    request_count = fields.Integer(compute='_compute_request_count')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    def _compute_request_count(self):
        for plan in self:
            plan.request_count = len(plan.request_ids)

    def _create_request(self):
        self.ensure_one()
        request = self.env['inom.maintenance.request'].create({
            'title': self.work_summary or self.name,
            'asset_id': self.asset_id.id,
            'request_type': 'preventive',
            'priority': self.priority,
            'description': self.instruction,
            'plan_id': self.id,
        })
        self.message_post(body=_(
            'Preventive request %s generated.', request.name))
        return request

    def _advance_next_due(self):
        self.ensure_one()
        base = self.next_due_date or fields.Date.context_today(self)
        delta_map = {
            'days': relativedelta(days=self.interval_number),
            'weeks': relativedelta(weeks=self.interval_number),
            'months': relativedelta(months=self.interval_number),
            'years': relativedelta(years=self.interval_number),
        }
        self.next_due_date = base + delta_map[self.interval_unit or 'months']

    @api.model
    def _cron_generate_time_based(self):
        today = fields.Date.context_today(self)
        plans = self.search([
            ('trigger_type', '=', 'time'),
            ('next_due_date', '!=', False),
        ])
        for plan in plans:
            create_on = fields.Date.subtract(
                plan.next_due_date, days=plan.lead_days or 0)
            if today >= create_on:
                open_existing = plan.request_ids.filtered(
                    lambda r: r.state not in ('done', 'cancelled'))
                if not open_existing:
                    plan._create_request()
                plan._advance_next_due()

    @api.model
    def _check_meter_trigger(self, meter):
        """Called whenever a new reading arrives on a cumulative meter."""
        plans = self.search([
            ('trigger_type', '=', 'meter'),
            ('meter_id', '=', meter.id),
            ('meter_interval', '>', 0),
        ])
        for plan in plans:
            current = meter.last_reading_value
            if current - plan.last_triggered_value >= plan.meter_interval:
                open_existing = plan.request_ids.filtered(
                    lambda r: r.state not in ('done', 'cancelled'))
                if not open_existing:
                    plan._create_request()
                plan.last_triggered_value = current

    def action_view_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Requests'),
            'res_model': 'inom.maintenance.request',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
        }
