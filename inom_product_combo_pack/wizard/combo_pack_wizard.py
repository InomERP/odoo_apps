# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ComboPackWizard(models.TransientModel):
    _name = 'combo.pack.wizard'
    _description = 'Add Combo Pack Wizard'

    order_model = fields.Char(string='Order Model', required=True)
    order_id = fields.Integer(string='Order ID', required=True)
    explode = fields.Boolean(string='Explode Pack Items')
    pack_id = fields.Many2one(
        comodel_name='product.template',
        string='Combo Pack',
        required=True,
        domain=[('is_combo_pack', '=', True)],
    )
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    price_unit = fields.Float(
        string='Pack Price',
        help='Price of the whole pack. Used only when the pack is added as a '
             'single line (normal mode).',
    )
    line_ids = fields.One2many(
        comodel_name='combo.pack.wizard.line',
        inverse_name='wizard_id',
        string='Pack Items',
    )

    @api.onchange('pack_id')
    def _onchange_pack_id(self):
        self.line_ids = [(5, 0, 0)]
        if self.pack_id:
            self.price_unit = self.pack_id.list_price
            new_lines = []
            for pack_line in self.pack_id.pack_line_ids:
                new_lines.append((0, 0, {
                    'product_id': pack_line.product_id.id,
                    'quantity': pack_line.quantity,
                    'price_unit': (
                        pack_line.unit_price or pack_line.product_id.lst_price
                    ),
                }))
            self.line_ids = new_lines

    def action_add_pack(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('The selected combo pack has no component items.'))
        if self.order_model == 'sale.order':
            self._add_to_sale_order()
        elif self.order_model == 'purchase.order':
            self._add_to_purchase_order()
        else:
            raise UserError(_('Unsupported order type for combo packs.'))
        return {'type': 'ir.actions.act_window_close'}

    def _add_to_sale_order(self):
        order = self.env['sale.order'].browse(self.order_id)
        sale_line_model = self.env['sale.order.line']
        if self.explode:
            for line in self.line_ids:
                sale_line_model.create({
                    'order_id': order.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity * self.quantity,
                    'price_unit': line.price_unit,
                    'pack_id': self.pack_id.id,
                    'is_pack_component': True,
                })
        else:
            sale_line_model.create({
                'order_id': order.id,
                'product_id': self.pack_id.product_variant_id.id,
                'product_uom_qty': self.quantity,
                'price_unit': self.price_unit,
                'pack_id': self.pack_id.id,
                'is_pack_parent': True,
            })
            for line in self.line_ids:
                sale_line_model.create({
                    'order_id': order.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity * self.quantity,
                    'price_unit': 0.0,
                    'pack_id': self.pack_id.id,
                    'is_pack_component': True,
                })

    def _add_to_purchase_order(self):
        order = self.env['purchase.order'].browse(self.order_id)
        purchase_line_model = self.env['purchase.order.line']
        if self.explode:
            for line in self.line_ids:
                purchase_line_model.create({
                    'order_id': order.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity * self.quantity,
                    'price_unit': line.price_unit,
                    'pack_id': self.pack_id.id,
                    'is_pack_component': True,
                })
        else:
            purchase_line_model.create({
                'order_id': order.id,
                'product_id': self.pack_id.product_variant_id.id,
                'product_qty': self.quantity,
                'price_unit': self.price_unit,
                'pack_id': self.pack_id.id,
                'is_pack_parent': True,
            })
            for line in self.line_ids:
                purchase_line_model.create({
                    'order_id': order.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity * self.quantity,
                    'price_unit': 0.0,
                    'pack_id': self.pack_id.id,
                    'is_pack_component': True,
                })


class ComboPackWizardLine(models.TransientModel):
    _name = 'combo.pack.wizard.line'
    _description = 'Add Combo Pack Wizard Line'

    wizard_id = fields.Many2one(
        comodel_name='combo.pack.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
    )
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price')
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True,
    )
