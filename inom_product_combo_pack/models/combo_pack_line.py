# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ComboPackLine(models.Model):
    _name = 'combo.pack.line'
    _description = 'Combo Pack Item'
    _order = 'sequence, id'

    pack_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Combo Pack',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Component Product',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True,
    )
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
    )

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.unit_price = line.product_id.lst_price
