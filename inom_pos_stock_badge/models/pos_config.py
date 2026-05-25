# -*- coding: utf-8 -*-
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
        store=True,
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

    stock_qty_validation = fields.Boolean(
        string='Stock Quantity Validation',
        default=True,
        help='Shows a warning if ordered qty exceeds available stock. Consumable/Service products are exempt.',
    )


    def write(self, vals):
        """
        Fix Odoo 17 core bug — IndexError when saving POS settings.
        available_pricelist_ids is sometimes passed as malformed ORM command.
        Core crash: pos_config.py line 439 → vals[key][0][2]
        """
        if "available_pricelist_ids" in vals:
            pl = vals["available_pricelist_ids"]
            if not pl or not isinstance(pl[0], (list, tuple)) or len(pl[0]) < 3:
                vals.pop("available_pricelist_ids")
        return super().write(vals)

    def get_pos_ui_pos_config(self):
        result = super().get_pos_ui_pos_config()
        extra_fields = [
            'display_stock',
            'stock_type',
            'badge_position',
            'badge_bg_color',
            'badge_font_color',
            'low_stock_threshold',
            'allow_order_out_of_stock',
            'deny_order_below_qty',
            'show_low_stock_button',
            'show_stock_of',
            'stock_location_id',
            'product_low_stock',
            'stock_qty_validation',
        ]
        for record, vals in zip(self, result):
            for field in extra_fields:
                val = record[field]
                if hasattr(val, 'id'):
                    vals[field] = [val.id, val.display_name] if val else False
                else:
                    vals[field] = val
        return result


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
    stock_qty_validation = fields.Boolean(
        related='pos_config_id.stock_qty_validation',
        readonly=False,
        string='Stock Quantity Validation',
    )

    @api.onchange('show_stock_of')
    def _onchange_show_stock_of(self):
        if self.show_stock_of == 'current_session':
            if not self.stock_location_id:
                warehouse = self.pos_config_id.warehouse_id
                if warehouse:
                    self.stock_location_id = warehouse.lot_stock_id
        else:
            self.stock_location_id = False


    def set_values(self):
        super().set_values()
        self.pos_config_id.write({
            'badge_bg_color': self.badge_bg_color,
            'badge_font_color': self.badge_font_color,
            'badge_position': self.badge_position,
            'display_stock': self.display_stock,
            'stock_type': self.stock_type,
            'low_stock_threshold': self.low_stock_threshold,
            'allow_order_out_of_stock': self.allow_order_out_of_stock,
            'deny_order_below_qty': self.deny_order_below_qty,
            'show_low_stock_button': self.show_low_stock_button,
            'show_stock_of': self.show_stock_of,
            'stock_location_id': self.stock_location_id.id if self.stock_location_id else False,
            'stock_qty_validation': self.stock_qty_validation,
        })