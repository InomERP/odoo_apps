# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models


class PosConfig(models.Model):

    _inherit = 'pos.config'


    display_stock = fields.Boolean(
        string='Display Stock in POS',
        default=False,
        help='Master toggle — enables stock badge on POS product cards.',
    )

    stock_type = fields.Selection(
        selection=[
            ('on_hand', 'Qty on Hand'),
            ('available', 'Qty Available'),
        ],
        string='Stock Type',
        default='on_hand',
        help='Qty on Hand = total physical stock. Qty Available = on hand minus reserved.',
    )


    badge_position = fields.Selection(
        selection=[
            ('top_left', 'Top Left'),
            ('top_right', 'Top Right'),
            ('bottom_right', 'Bottom Right'),
        ],
        string='Badge Position',
        default='top_left',
        help='Position of the stock badge on each product card.',
    )

    badge_bg_color = fields.Char(
        string='Badge Background Color',
        default='#28A745',
        help='Hex color code for normal-stock badge background.',
    )

    badge_font_color = fields.Char(
        string='Badge Font Color',
        default='#FFFFFF',
        help='Hex color code for badge text.',
    )

    low_stock_threshold = fields.Float(
        string='Low Stock Threshold',
        default=5.0,
        help='Products at or below this quantity will show an orange badge.',
    )

    allow_order_out_of_stock = fields.Boolean(
        string='Allow Order Out of Stock',
        default=True,
        help='When disabled, cashier cannot add out-of-stock products to cart.',
    )

    deny_order_below_qty = fields.Integer(
        string='Deny Order Below Qty',
        default=0,
        help='Block order if remaining stock would fall below this value. Set 0 to disable.',
    )

    show_low_stock_button = fields.Boolean(
        string='Show Low Stock Button',
        default=True,
        help='Adds Low Stock button in POS toolbar.',
    )


    show_stock_of = fields.Selection(
        selection=[
            ('all_warehouse', 'All Warehouse'),
            ('current_session', 'Current Session Warehouse'),
        ],
        string='Show Stock Of',
        default='all_warehouse',
        help='Product stock location type.',
    )

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        help='Stock location used for inventory.',
        domain=[('usage', '=', 'internal')],
    )

    product_low_stock = fields.Float(
        string='Product Low Stock',
        default=5.0,
        help='Below this quantity product is considered low stock.',
    )

    def _get_inom_stock_location(self):
        """ Location whose stock is shown in POS; empty recordset = all internal locations. """
        self.ensure_one()
        if self.show_stock_of != 'current_session':
            return self.env['stock.location']
        return self.stock_location_id or self.picking_type_id.default_location_src_id

    def get_inom_pos_stock(self, product_tmpl_ids):
        """ Return {template_id: qty} for the storable templates in ``product_tmpl_ids``,
        using the location and stock type configured on this POS. """
        self.ensure_one()
        location = self._get_inom_stock_location()
        ctx = {'location': location.id} if location else {}
        # Only this POS's company: stock of other allowed companies must not be counted.
        ctx['allowed_company_ids'] = [self.company_id.id]
        products = self.env['product.product'].with_context(**ctx).search([
            ('product_tmpl_id', 'in', product_tmpl_ids),
            ('is_storable', '=', True),
        ])
        qty_field = 'free_qty' if self.stock_type == 'available' else 'qty_available'
        result = defaultdict(float)
        for product in products:
            result[product.product_tmpl_id.id] += product[qty_field]
        for product, qty in self._get_inom_unpicked_pos_qty(products, location).items():
            result[product.product_tmpl_id.id] -= qty
        return dict(result)

    def _get_inom_unpicked_pos_qty(self, products, location):
        """ Qty sold in still-open sessions that update stock at closing: these orders
        have no picking yet, so they are not reflected in the stock quantities. """
        if not products:
            return {}
        domain = [
            ('product_id', 'in', products.ids),
            ('order_id.state', 'in', ('paid', 'done')),
            ('order_id.picking_ids', '=', False),
            ('order_id.session_id.state', '!=', 'closed'),
            ('order_id.session_id.update_stock_at_closing', '=', True),
            ('company_id', '=', self.company_id.id),
        ]
        if location:
            domain.append(('order_id.config_id.picking_type_id.default_location_src_id', 'child_of', location.id))
        groups = self.env['pos.order.line'].sudo()._read_group(domain, ['product_id'], ['qty:sum'])
        return {product.with_env(self.env): qty for product, qty in groups}


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    display_stock = fields.Boolean(
        related='pos_config_id.display_stock',
        readonly=False,
        string='Display Stock in POS',
    )
    allow_order_out_of_stock = fields.Boolean(
        related='pos_config_id.allow_order_out_of_stock',
        readonly=False,
        string='Allow Order Out of Stock',
    )
    stock_type = fields.Selection(
        related='pos_config_id.stock_type',
        readonly=False,
        string='Stock Type',
    )
    badge_position = fields.Selection(
        related='pos_config_id.badge_position',
        readonly=False,
        string='Badge Position',
    )
    badge_bg_color = fields.Char(
        related='pos_config_id.badge_bg_color',
        readonly=False,
        string='Badge Background Color',
    )
    badge_font_color = fields.Char(
        related='pos_config_id.badge_font_color',
        readonly=False,
        string='Badge Font Color',
    )
    low_stock_threshold = fields.Float(
        related='pos_config_id.low_stock_threshold',
        readonly=False,
        string='Low Stock Threshold',
    )
    deny_order_below_qty = fields.Integer(
        related='pos_config_id.deny_order_below_qty',
        readonly=False,
        string='Deny Order Below Qty',
    )
    show_low_stock_button = fields.Boolean(
        related='pos_config_id.show_low_stock_button',
        readonly=False,
        string='Show Low Stock Button',
    )
    show_stock_of = fields.Selection(
        related='pos_config_id.show_stock_of',
        readonly=False,
        string='Show Stock Of',
    )
    stock_location_id = fields.Many2one(
        related='pos_config_id.stock_location_id',
        readonly=False,
        string='Stock Location',
    )
    product_low_stock = fields.Float(
        related='pos_config_id.product_low_stock',
        readonly=False,
        string='Product Low Stock',
    )

    @api.onchange('show_stock_of')
    def _onchange_show_stock_of(self):
        if self.show_stock_of == 'current_session':
            if not self.stock_location_id:
                self.stock_location_id = self.pos_config_id.picking_type_id.default_location_src_id
        else:
            self.stock_location_id = False
