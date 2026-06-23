# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockInventoryCountProductLine(models.Model):
    _name = 'stock.inventory.count.product.line'
    _description = 'Inventory Count Product Line'

    count_id = fields.Many2one(
        'stock.inventory.count',
        string='Inventory Count',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='count_id.company_id',
        string='Company',
        store=True,
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        check_company=True,
        domain="[('is_storable', '=', True)]",
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

    _sql_constraints = [
        (
            'product_uniq_per_count',
            'unique(count_id, product_id)',
            'This product is already added to the inventory count.',
        ),
    ]


class StockInventoryCountLine(models.Model):
    _name = 'stock.inventory.count.line'
    _description = 'Inventory Count Line'

    count_id = fields.Many2one(
        'stock.inventory.count',
        string='Inventory Count',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='count_id.company_id',
        string='Company',
        store=True,
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
    )
    theoretical_qty = fields.Float(
        string='Theoretical Quantity',
        help='System quantity captured from stock.quant when the '
             'counting was completed.',
    )
    counted_qty = fields.Float(
        string='Counted Quantity',
        help='Aggregated counted quantity from all submitted sessions.',
    )
    discrepancy = fields.Float(
        string='Discrepancy',
        compute='_compute_discrepancy',
        store=True,
        help='Counted quantity minus theoretical quantity.',
    )
    user_calculation_mistake = fields.Boolean(
        string='Calculation Mistake',
    )
    warehouse_id = fields.Many2one(
        related='count_id.warehouse_id',
        string='Warehouse',
        store=True,
        index=True,
    )
    date = fields.Date(
        related='count_id.date',
        string='Count Date',
        store=True,
    )
    count_state = fields.Selection(
        related='count_id.state',
        string='Count Status',
        store=True,
    )
    adjustment_type = fields.Selection(
        selection=[
            ('overstock', 'Overstock'),
            ('out_of_stock', 'Out of Stock'),
            ('balanced', 'Balanced'),
        ],
        string='Adjustment Type',
        compute='_compute_adjustment_type',
        store=True,
    )

    @api.depends('counted_qty', 'theoretical_qty')
    def _compute_discrepancy(self):
        for line in self:
            line.discrepancy = line.counted_qty - line.theoretical_qty

    @api.depends('discrepancy')
    def _compute_adjustment_type(self):
        for line in self:
            if line.discrepancy > 0:
                line.adjustment_type = 'overstock'
            elif line.discrepancy < 0:
                line.adjustment_type = 'out_of_stock'
            else:
                line.adjustment_type = 'balanced'
