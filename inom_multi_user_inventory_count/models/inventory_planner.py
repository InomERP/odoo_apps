# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockInventoryCountPlanner(models.Model):
    _name = 'stock.inventory.count.planner'
    _description = 'Inventory Count Planner'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        default=lambda self: self.env.user,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        check_company=True,
    )
    allowed_location_ids = fields.Many2many(
        'stock.location',
        string='Allowed Locations',
        compute='_compute_allowed_location_ids',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        check_company=True,
        domain="[('id', 'in', allowed_location_ids)]",
    )
    frequency_days = fields.Integer(
        string='Frequency (Days)',
        required=True,
        default=30,
        help='A new inventory count is created when this many days have '
             'passed since the last run.',
    )
    session_type = fields.Selection(
        selection=[
            ('single', 'Single Session'),
            ('multi', 'Multi Session'),
        ],
        string='Count Type',
        required=True,
        default='single',
    )
    use_barcode_scanner = fields.Boolean(
        string='Use Barcode Scanner',
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        domain="[('is_storable', '=', True)]",
        help='Products to include in each automatically created count.',
    )
    last_run = fields.Datetime(
        string='Last Run',
        readonly=True,
        copy=False,
    )
    count_ids = fields.One2many(
        'stock.inventory.count',
        'planner_id',
        string='Created Counts',
    )
    count_count = fields.Integer(
        string='Count Count',
        compute='_compute_count_count',
    )

    @api.depends('warehouse_id')
    def _compute_allowed_location_ids(self):
        location_obj = self.env['stock.location']
        for planner in self:
            domain = [('usage', '=', 'internal')]
            if planner.warehouse_id:
                domain = [
                    ('id', 'child_of', planner.warehouse_id.view_location_id.id),
                    ('usage', '=', 'internal'),
                ]
            planner.allowed_location_ids = location_obj.search(domain)

    @api.depends('count_ids')
    def _compute_count_count(self):
        for planner in self:
            planner.count_count = len(planner.count_ids)

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.location_id and self.location_id not in self.allowed_location_ids:
            self.location_id = False

    def _create_count(self):
        self.ensure_one()
        count = self.env['stock.inventory.count'].create({
            'approver_id': (self.approver_id or self.env.user).id,
            'warehouse_id': self.warehouse_id.id,
            'location_id': self.location_id.id,
            'session_type': self.session_type,
            'use_barcode_scanner': self.use_barcode_scanner,
            'planner_id': self.id,
            'product_line_ids': [
                (0, 0, {'product_id': product.id})
                for product in self.product_ids
            ],
        })
        return count

    def action_run_now(self):
        self.ensure_one()
        count = self._create_count()
        self.last_run = fields.Datetime.now()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.inventory.count',
            'view_mode': 'form',
            'res_id': count.id,
            'target': 'current',
        }

    def action_view_counts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Counts'),
            'res_model': 'stock.inventory.count',
            'view_mode': 'list,form',
            'domain': [('planner_id', '=', self.id)],
        }

    @api.model
    def _cron_create_counts(self):
        """Scheduled action: create counts for planners that are due."""
        now = fields.Datetime.now()
        for planner in self.search([('active', '=', True)]):
            if planner.last_run and (now - planner.last_run) < timedelta(
                    days=planner.frequency_days):
                continue
            planner._create_count()
            planner.last_run = now
