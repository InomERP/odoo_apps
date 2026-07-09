# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InomAssetCategory(models.Model):
    _name = 'inom.asset.category'
    _description = 'Asset Category'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    code = fields.Char(string='Category Code')
    complete_name = fields.Char(
        string='Complete Name', compute='_compute_complete_name',
        recursive=True, store=True)
    parent_id = fields.Many2one(
        'inom.asset.category', string='Parent Category',
        index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'inom.asset.category', 'parent_id', string='Sub Categories')
    asset_ids = fields.One2many('inom.asset', 'category_id', string='Assets')
    asset_count = fields.Integer(
        string='Asset Count', compute='_compute_asset_count')
    color = fields.Integer(string='Color Index')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    # Depreciation defaults inherited by assets of this category
    depreciation_method = fields.Selection([
        ('linear', 'Straight Line'),
        ('declining', 'Declining Balance'),
    ], string='Default Depreciation Method', default='linear')
    depreciation_years = fields.Integer(
        string='Default Life (Years)', default=5)
    declining_factor = fields.Float(
        string='Default Declining Factor', default=2.0)
    note = fields.Html(string='Notes')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (
                    category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def _compute_asset_count(self):
        grouped = self.env['inom.asset']._read_group(
            [('category_id', 'in', self.ids)],
            ['category_id'], ['__count'])
        counts = {cat.id: count for cat, count in grouped}
        for category in self:
            category.asset_count = counts.get(category.id, 0)

    def action_view_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assets',
            'res_model': 'inom.asset',
            'view_mode': 'list,form,kanban',
            'domain': [('category_id', 'child_of', self.id)],
            'context': {'default_category_id': self.id},
        }
