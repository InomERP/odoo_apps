# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InomRateCard(models.Model):
    _name = 'inom.rate.card'
    _description = 'Job Cost Rate Card'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    note = fields.Text(string='Notes')
    line_ids = fields.One2many('inom.rate.card.line', 'card_id', string='Rates')
    line_count = fields.Integer(compute='_compute_line_count')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for card in self:
            card.line_count = len(card.line_ids)

    def rate_for_product(self, product):
        """Return the rate for a product from this card, or None."""
        self.ensure_one()
        if not product:
            return None
        line = self.line_ids.filtered(
            lambda l: l.kind == 'material' and l.product_id == product)[:1]
        return line.rate if line else None

    def rate_for_labour(self, label):
        """Return the manpower rate matching a label, or None."""
        self.ensure_one()
        if not label:
            return None
        key = label.strip().lower()
        line = self.line_ids.filtered(
            lambda l: l.kind == 'labour' and (l.name or '').strip().lower() == key)[:1]
        return line.rate if line else None


class InomRateCardLine(models.Model):
    _name = 'inom.rate.card.line'
    _description = 'Job Cost Rate Card Line'
    _order = 'kind, sequence, id'

    sequence = fields.Integer(default=10)
    card_id = fields.Many2one('inom.rate.card', string='Rate Card',
                              required=True, ondelete='cascade')
    kind = fields.Selection(
        [('material', 'Material'), ('labour', 'Manpower')],
        string='Type', required=True, default='material')
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Description')
    rate = fields.Float(string='Rate', required=True)
    currency_id = fields.Many2one(related='card_id.company_id.currency_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.kind == 'material' and line.product_id:
                if not line.name:
                    line.name = line.product_id.display_name
                if not line.rate:
                    line.rate = line.product_id.standard_price
