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

    @api.depends('quantity', 'price_unit', 'tax_ids', 'currency_id',
                 'product_id', 'contract_id.partner_id', 'contract_id.company_id')
    def _compute_amounts(self):
        Tax = self.env['account.tax']
        for line in self:
            base = line.quantity * line.price_unit
            if not line.tax_ids:
                line.price_subtotal = base
                line.price_total = base
                line.price_tax = 0.0
                continue

            # Odoo 20 uses the batch tax-computation engine; the legacy
            # account.tax.compute_all() API is no longer available.
            base_line = Tax._prepare_base_line_for_taxes_computation(
                line,
                price_unit=line.price_unit,
                quantity=line.quantity,
                tax_ids=line.tax_ids,
                product_id=line.product_id,
                partner_id=line.contract_id.partner_id,
                currency_id=line.currency_id,
                discount=0.0,
            )
            Tax._add_tax_details_in_base_lines(
                [base_line],
                line.contract_id.company_id,
            )
            Tax._round_base_lines_tax_details(
                [base_line],
                line.contract_id.company_id,
            )
            tax_details = base_line['tax_details']
            line.price_subtotal = tax_details['total_excluded_currency']
            line.price_total = tax_details['total_included_currency']
            line.price_tax = (
                tax_details['total_included_currency']
                - tax_details['total_excluded_currency']
            )

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
