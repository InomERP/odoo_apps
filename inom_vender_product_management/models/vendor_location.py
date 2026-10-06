# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VendorLocation(models.Model):
    _name = 'vendor.location'
    _description = 'Vendor Stock Location'
    _order = 'vendor_id, name'

    name = fields.Char(
        string='Location Name',
        required=True,
        help="e.g. 'Main Warehouse', 'Shanghai DC'.",
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        ondelete='restrict',
        domain=[('supplier_rank', '>', 0)],
        help="The supplier this stock location belongs to.",
    )
    address = fields.Text(string='Address')
    delivery_lead_time = fields.Float(
        string='Avg. Delivery Time (Days)',
        help="Average number of days for stock from this location to arrive.",
    )
    active = fields.Boolean(default=True)
    stock_ids = fields.One2many(
        'vendor.stock',
        'location_id',
        string='Stock Lines',
    )

    @api.depends('name', 'vendor_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.vendor_id:
                rec.display_name = f"{rec.vendor_id.name} - {rec.name}"
            else:
                rec.display_name = rec.name or ''
