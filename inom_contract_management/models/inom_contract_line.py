# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InomContractLine(models.Model):
    _name = 'inom.contract.line'
    _description = 'Contract Line'
    _order = 'contract_id, sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    contract_id = fields.Many2one(
        comodel_name='inom.contract',
        string='Contract',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='contract_id.company_id',
        string='Company',
        store=True,
    )
    currency_id = fields.Many2one(
        related='contract_id.currency_id',
        string='Currency',
        store=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )
    name = fields.Char(
        string='Description',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        digits='Product Unit of Measure',
    )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price',
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    price_tax = fields.Monetary(
        string='Tax Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('quantity', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_amounts(self):
        for line in self:
            base = line.quantity * line.price_unit
            if line.tax_ids:
                taxes = line.tax_ids.compute_all(
                    line.price_unit,
                    currency=line.currency_id,
                    quantity=line.quantity,
                    product=line.product_id,
                    partner=line.contract_id.partner_id,
                )
                line.price_subtotal = taxes['total_excluded']
                line.price_total = taxes['total_included']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
            else:
                line.price_subtotal = base
                line.price_total = base
                line.price_tax = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if not product:
                continue
            if not line.name:
                line.name = product.display_name
            contract_type = line.contract_id.contract_type
            if contract_type == 'purchase':
                line.price_unit = product.standard_price
                line.tax_ids = product.supplier_taxes_id
            else:
                line.price_unit = product.lst_price
                line.tax_ids = product.taxes_id
