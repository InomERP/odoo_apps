# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InomCostCategory(models.Model):
    _name = 'inom.cost.category'
    _description = 'Job Cost Category'
    _order = 'name'

    name = fields.Char(string='Category', required=True)
    code = fields.Char(string='Code')
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(string='Active', default=True)
    note = fields.Text(string='Description')
    default_markup = fields.Float(
        string='Default Markup (%)',
        help='Applied to new estimates in this category. Used as the '
             'suggestion when there is not enough history to average.')
    estimate_count = fields.Integer(compute='_compute_estimate_count', string='Estimates')

    _name_uniq = models.Constraint(
        'unique(name)', 'The job category name must be unique.')

    def _compute_estimate_count(self):
        grouped = self.env['inom.cost.estimate']._read_group(
            [('category_id', 'in', self.ids)],
            groupby=['category_id'], aggregates=['__count'])
        mapped = {category.id: count for category, count in grouped}
        for rec in self:
            rec.estimate_count = mapped.get(rec.id, 0)
