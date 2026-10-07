# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InomAssetLocation(models.Model):
    _name = 'inom.asset.location'
    _description = 'Asset Location'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Location Name', required=True, translate=True)
    complete_name = fields.Char(
        string='Complete Name', compute='_compute_complete_name',
        recursive=True, store=True)
    parent_id = fields.Many2one(
        'inom.asset.location', string='Parent Location',
        index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'inom.asset.location', 'parent_id', string='Sub Locations')
    responsible_id = fields.Many2one(
        'hr.employee', string='Location In-Charge')
    address = fields.Text(string='Address')
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)
    asset_ids = fields.One2many('inom.asset', 'location_id', string='Assets')
    asset_count = fields.Integer(
        string='Asset Count', compute='_compute_asset_count')
    active = fields.Boolean(default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for location in self:
            if location.parent_id:
                location.complete_name = '%s / %s' % (
                    location.parent_id.complete_name, location.name)
            else:
                location.complete_name = location.name

    def _compute_asset_count(self):
        grouped = self.env['inom.asset']._read_group(
            [('location_id', 'in', self.ids)],
            ['location_id'], ['__count'])
        counts = {loc.id: count for loc, count in grouped}
        for location in self:
            location.asset_count = counts.get(location.id, 0)

    def action_view_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assets',
            'res_model': 'inom.asset',
            'view_mode': 'list,form,kanban',
            'domain': [('location_id', 'child_of', self.id)],
            'context': {'default_location_id': self.id},
        }
