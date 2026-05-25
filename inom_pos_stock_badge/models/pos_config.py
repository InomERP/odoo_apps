# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    display_stock = fields.Boolean(string='Display Stock in POS', default=False)
    stock_type = fields.Selection(
        selection=[('on_hand', 'Qty on Hand'), ('available', 'Qty Available')],
        string='Stock Type', default='on_hand',
    )
    badge_position = fields.Selection(
        selection=[('top_left', 'Top Left'), ('top_right', 'Top Right'), ('bottom_right', 'Bottom Right')],
        string='Badge Position', default='top_left',
    )
    badge_bg_color = fields.Char(string='Badge Background Color', default='#28A745')
    badge_font_color = fields.Char(string='Badge Font Color', default='#FFFFFF')
    low_stock_threshold = fields.Float(string='Low Stock Threshold', default=5.0)
    allow_order_out_of_stock = fields.Boolean(string='Allow Order Out of Stock', default=True, store=True)
    deny_order_below_qty = fields.Integer(string='Deny Order Below Qty', default=0)
    show_low_stock_button = fields.Boolean(string='Show Low Stock Button', default=True)
    show_stock_of = fields.Selection(
        selection=[('all_warehouse', 'All Warehouse'), ('current_session', 'Current Session Warehouse')],
        string='Show Stock Of', default='all_warehouse',
    )
    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location',
        domain=[('usage', '=', 'internal')]
    )
    product_low_stock = fields.Float(string='Product Low Stock', default=5.0)

    def _load_pos_data(self, data):
        result = super()._load_pos_data(data)
        for record_vals in result.get('data', []):
            record = self.browse(record_vals['id'])
            record_vals['display_stock'] = record.display_stock
            record_vals['stock_type'] = record.stock_type or 'on_hand'
            record_vals['badge_position'] = record.badge_position or 'top_left'
            record_vals['badge_bg_color'] = record.badge_bg_color or '#28A745'
            record_vals['badge_font_color'] = record.badge_font_color or '#FFFFFF'
            record_vals['low_stock_threshold'] = record.low_stock_threshold
            record_vals['allow_order_out_of_stock'] = record.allow_order_out_of_stock
            record_vals['deny_order_below_qty'] = record.deny_order_below_qty
            record_vals['show_low_stock_button'] = record.show_low_stock_button
            record_vals['show_stock_of'] = record.show_stock_of or 'all_warehouse'
            record_vals['stock_location_id'] = record.stock_location_id.id if record.stock_location_id else False
            record_vals['product_low_stock'] = record.product_low_stock

        if result.get('data'):
            result['fields'] = list(result['data'][0].keys())
        return result


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    display_stock = fields.Boolean(related='pos_config_id.display_stock', readonly=False)
    allow_order_out_of_stock = fields.Boolean(related='pos_config_id.allow_order_out_of_stock', readonly=False)
    stock_type = fields.Selection(related='pos_config_id.stock_type', readonly=False)
    badge_position = fields.Selection(related='pos_config_id.badge_position', readonly=False)
    badge_bg_color = fields.Char(related='pos_config_id.badge_bg_color', readonly=False)
    badge_font_color = fields.Char(related='pos_config_id.badge_font_color', readonly=False)
    low_stock_threshold = fields.Float(related='pos_config_id.low_stock_threshold', readonly=False)
    deny_order_below_qty = fields.Integer(related='pos_config_id.deny_order_below_qty', readonly=False)
    show_low_stock_button = fields.Boolean(related='pos_config_id.show_low_stock_button', readonly=False)
    show_stock_of = fields.Selection(related='pos_config_id.show_stock_of', readonly=False)
    stock_location_id = fields.Many2one(related='pos_config_id.stock_location_id', readonly=False)
    product_low_stock = fields.Float(related='pos_config_id.product_low_stock', readonly=False)

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
        if self.pos_config_id:
            self.pos_config_id.sudo().write({
                'stock_type': self.stock_type,
                'show_stock_of': self.show_stock_of,
                'stock_location_id': self.stock_location_id.id if self.stock_location_id else False,
            })