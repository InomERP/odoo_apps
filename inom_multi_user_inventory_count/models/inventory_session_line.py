# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockInventorySessionLine(models.Model):
    _name = 'stock.inventory.session.line'
    _description = 'Inventory Count Session Line'

    session_id = fields.Many2one(
        'stock.inventory.count.session',
        string='Session',
        required=True,
        ondelete='cascade',
        index=True,
    )
    user_id = fields.Many2one(
        related='session_id.user_id',
        string='Assigned User',
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        related='session_id.company_id',
        string='Company',
        store=True,
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    default_code = fields.Char(
        related='product_id.default_code',
        string='Internal Reference',
        readonly=True,
    )
    barcode = fields.Char(
        related='product_id.barcode',
        string='Barcode',
        readonly=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
    )
    counted_qty = fields.Float(
        string='Counted Quantity',
        default=0.0,
    )
    scanned = fields.Boolean(
        string='Scanned',
        default=False,
        copy=False,
    )
    user_calculation_mistake = fields.Boolean(
        string='Calculation Mistake',
        help='Flag this line when the counted quantity is suspected '
             'to contain a calculation mistake.',
    )
    mistake_count = fields.Integer(
        string='Mistake Count',
        compute='_compute_mistake_count',
        store=True,
        help='Technical measure used by the User Statistic report '
             '(1 when a calculation mistake is flagged, else 0).',
    )
    # State is defined here for the line lifecycle. The approve / reject
    # actions that drive it are implemented in Phase 4.
    state = fields.Selection(
        selection=[
            ('pending_review', 'Pending Review'),
            ('approve', 'Approved'),
            ('reject', 'Rejected'),
        ],
        string='Line Status',
        default='pending_review',
        required=True,
        copy=False,
    )

    @api.depends('user_calculation_mistake')
    def _compute_mistake_count(self):
        for line in self:
            line.mistake_count = 1 if line.user_calculation_mistake else 0

    def action_scan(self):
        self.write({'scanned': True})

    def action_unscan(self):
        self.write({'scanned': False})

    def action_approve(self):
        self.write({'state': 'approve'})

    def action_reject(self):
        self.write({'state': 'reject'})
