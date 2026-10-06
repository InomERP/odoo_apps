# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VendorStock(models.Model):
    _name = 'vendor.stock'
    _description = 'Vendor Stock Level'
    _order = 'vendor_product_id, location_id'

    vendor_product_id = fields.Many2one(
        'vendor.product',
        string='Vendor Product',
        required=True,
        ondelete='cascade',
    )
    location_id = fields.Many2one(
        'vendor.location',
        string='Vendor Location',
        required=True,
        ondelete='restrict',
    )
    vendor_id = fields.Many2one(
        related='vendor_product_id.vendor_id',
        string='Vendor',
        store=True,
        readonly=True,
        ondelete='set null',
    )
    quantity = fields.Float(
        string='Quantity (Vendor UoM)',
        required=True,
        default=0.0,
        help="Stock level as reported by the vendor, in the vendor's own unit of measure.",
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Vendor UoM',
        required=True,
        ondelete='restrict',
        help="The unit of measure the vendor reports this quantity in.",
    )
    product_uom_id = fields.Many2one(
        related='vendor_product_id.product_id.uom_id',
        string='Product UoM',
        readonly=True,
        ondelete='set null',
    )
    quantity_product_uom = fields.Float(
        string='Quantity (Product UoM)',
        compute='_compute_quantity_product_uom',
        store=True,
        help="Vendor quantity converted into your product's unit of measure.",
    )
    uom_mismatch = fields.Boolean(
        string='UoM Mismatch',
        compute='_compute_quantity_product_uom',
        store=True,
        help="True when the vendor UoM and the product UoM are not in the "
             "same category, so no automatic conversion is possible.",
    )
    last_updated = fields.Datetime(
        string='Last Updated',
        default=fields.Datetime.now,
    )
    note = fields.Char(string='Note')
    active = fields.Boolean(
        default=True,
        help="Archived stock lines are kept for history but excluded from "
             "totals and lists. Lines can be archived automatically when "
             "re-importing a vendor's stock file.",
    )

    _vendor_product_location_uniq = models.Constraint(
        'unique(vendor_product_id, location_id)',
        'There is already a stock line for this vendor product at this location!',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_catalog_notify'):
            for record in records:
                record._notify_stock_event()
        return records

    def write(self, vals):
        qty_changing = 'quantity' in vals and not self.env.context.get('skip_catalog_notify')
        old_quantities = {rec.id: rec.quantity for rec in self} if qty_changing else {}
        res = super().write(vals)
        if qty_changing:
            for rec in self:
                if old_quantities.get(rec.id) != rec.quantity:
                    rec._notify_stock_event()
        return res

    def _notify_stock_event(self):
        """vendor.stock has no chatter of its own, so the notification is
        posted on the related vendor product (and, from there, on the
        vendor's own contact) instead."""
        self.ensure_one()
        if not self.vendor_product_id:
            return
        self.vendor_product_id._notify_catalog_event(
            'inom_vender_product_management.mt_vendor_product_stock_update',
            'inom_vender_product_management.mt_partner_vendor_product_stock_update',
            "New stock at %s: %s %s" % (
                self.location_id.name, self.quantity, self.uom_id.name,
            ),
        )

    @api.depends('quantity', 'uom_id', 'uom_id.relative_uom_id',
                 'vendor_product_id.product_id.uom_id',
                 'vendor_product_id.product_id.uom_id.relative_uom_id')
    def _compute_quantity_product_uom(self):
        for rec in self:
            product_uom = rec.vendor_product_id.product_id.uom_id
            if not rec.uom_id or not product_uom:
                rec.quantity_product_uom = rec.quantity
                rec.uom_mismatch = False
                continue
            if self._get_uom_reference(rec.uom_id) != self._get_uom_reference(product_uom):
                rec.uom_mismatch = True
                rec.quantity_product_uom = rec.quantity
            else:
                rec.uom_mismatch = False
                rec.quantity_product_uom = rec.uom_id._compute_quantity(
                    rec.quantity, product_uom
                )

    def _get_uom_reference(self, uom):
        """Walk up the relative_uom_id chain to find a UoM's root reference
        unit. Odoo 19 removed uom.category / category_id; UoMs now link
        directly to each other via relative_uom_id instead."""
        seen = uom.browse()
        while uom.relative_uom_id and uom.id not in seen.ids:
            seen |= uom
            uom = uom.relative_uom_id
        return uom

    @api.onchange('vendor_product_id')
    def _onchange_vendor_product_id(self):
        if self.vendor_product_id.product_id and not self.uom_id:
            self.uom_id = self.vendor_product_id.product_id.uom_id

    @api.onchange('vendor_product_id')
    def _onchange_vendor_product_id_location_domain(self):
        if self.vendor_product_id.vendor_id:
            return {
                'domain': {
                    'location_id': [('vendor_id', '=', self.vendor_product_id.vendor_id.id)],
                }
            }
