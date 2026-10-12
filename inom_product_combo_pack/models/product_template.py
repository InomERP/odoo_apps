# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_combo_pack = fields.Boolean(
        string='Is Combo Pack',
        help='Enable to sell this product as a combo pack made of several '
             'component products.',
    )
    auto_pack_price = fields.Boolean(
        string='Auto-Calculate Pack Price',
        help='When enabled, the sales price of the pack is calculated '
             'automatically from the total of its component lines.',
    )
    pack_line_ids = fields.One2many(
        comodel_name='combo.pack.line',
        inverse_name='pack_tmpl_id',
        string='Combo Pack Items',
        copy=True,
    )
    pack_items_price = fields.Float(
        string='Pack Items Total',
        compute='_compute_pack_items_price',
        help='Total of all component lines of the combo pack.',
    )
    available_pack_qty = fields.Float(
        string='Deliverable Packs',
        compute='_compute_available_pack_qty',
        help='Number of complete combo packs that can be delivered from the '
             'current on-hand stock of the component products.',
    )
    pack_availability_state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('partial', 'Partially Available'),
            ('out', 'Out of Stock'),
        ],
        string='Pack Availability',
        compute='_compute_available_pack_qty',
    )
    pack_total_cost = fields.Float(
        string='Pack Components Cost',
        compute='_compute_pack_margin',
        help='Total cost of the component products based on their cost price.',
    )
    pack_margin = fields.Float(
        string='Pack Margin',
        compute='_compute_pack_margin',
        help='Difference between the pack sales price and the total cost of '
             'its component products.',
    )
    pack_margin_percent = fields.Float(
        string='Pack Margin (%)',
        compute='_compute_pack_margin',
    )

    @api.depends('pack_line_ids.subtotal')
    def _compute_pack_items_price(self):
        for template in self:
            template.pack_items_price = sum(
                template.pack_line_ids.mapped('subtotal')
            )

    @api.depends('is_combo_pack', 'pack_line_ids.quantity',
                 'pack_line_ids.product_id',
                 'pack_line_ids.product_id.qty_available')
    def _compute_available_pack_qty(self):
        for template in self:
            capacities = []
            if template.is_combo_pack:
                for line in template.pack_line_ids:
                    if line.quantity <= 0 or not line.product_id:
                        continue
                    capacities.append(
                        line.product_id.qty_available // line.quantity
                    )
            available_qty = min(capacities) if capacities else 0.0
            template.available_pack_qty = available_qty
            if not capacities:
                template.pack_availability_state = 'out'
            elif available_qty <= 0:
                template.pack_availability_state = 'out'
            elif available_qty < 1:
                template.pack_availability_state = 'partial'
            else:
                template.pack_availability_state = 'available'

    @api.depends('is_combo_pack', 'list_price', 'pack_line_ids.quantity',
                 'pack_line_ids.product_id',
                 'pack_line_ids.product_id.standard_price')
    def _compute_pack_margin(self):
        for template in self:
            total_cost = 0.0
            if template.is_combo_pack:
                for line in template.pack_line_ids:
                    total_cost += line.product_id.standard_price * line.quantity
            margin = template.list_price - total_cost
            template.pack_total_cost = total_cost
            template.pack_margin = margin
            template.pack_margin_percent = (
                (margin / template.list_price) * 100.0
                if template.list_price else 0.0
            )

    @api.onchange('is_combo_pack')
    def _onchange_is_combo_pack(self):
        # A combo pack must invoice / bill on ordered quantities, because in
        # normal mode the pack price is carried by the parent line while the
        # stock movements are handled by the component lines.
        for template in self:
            if template.is_combo_pack:
                template.invoice_policy = 'order'
                if 'purchase_method' in template._fields:
                    template.purchase_method = 'purchase'

    @api.onchange('auto_pack_price', 'pack_line_ids', 'pack_items_price')
    def _onchange_auto_pack_price(self):
        for template in self:
            if template.is_combo_pack and template.auto_pack_price:
                template.list_price = template.pack_items_price
