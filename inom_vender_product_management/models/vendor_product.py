# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class VendorProduct(models.Model):
    _name = 'vendor.product'
    _description = 'Vendor Product'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'vendor_product_name'
    _order = 'vendor_id, vendor_product_name'

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        ondelete='restrict',
        tracking=True,
        domain=[('supplier_rank', '>', 0)],
        help="The supplier that offers this product.",
    )
    vendor_product_name = fields.Char(
        string='Vendor Product Name',
        required=True,
        tracking=True,
        help="The name the vendor uses for this product (may differ from ours).",
    )
    vendor_code = fields.Char(
        string='Vendor Product Code',
        tracking=True,
        help="The vendor's own reference / SKU for this product.",
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product Variant',
        ondelete='set null',
        tracking=True,
        help="The internal Odoo product variant this vendor product is matched to.",
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        related='product_id.product_tmpl_id',
        store=True,
        readonly=True,
        ondelete='set null',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        ondelete='set null',
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string='Notes')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        ondelete='set null',
        default=lambda self: self.env.company.currency_id,
    )
    vendor_price = fields.Monetary(
        string='Vendor Price',
        currency_field='currency_id',
        tracking=True,
        help="The price last reported by this vendor for this product.",
    )
    price_outdated = fields.Boolean(
        string='Price Outdated',
        tracking=True,
        help="Ticked when this price was flagged as outdated during an "
             "import (e.g. the vendor stopped reporting a price, or the "
             "file was re-imported without price data for this line).",
    )
    price_last_updated = fields.Datetime(
        string='Price Last Updated',
        help="When the vendor price was last set, manually or via import.",
    )
    stock_ids = fields.One2many(
        'vendor.stock',
        'vendor_product_id',
        string='Vendor Stock Lines',
    )
    total_vendor_stock_qty = fields.Float(
        string='Total Vendor Stock',
        compute='_compute_total_vendor_stock_qty',
        store=True,
        help="Sum of stock across all vendor locations, in your product's UoM. "
             "Informational only - not linked to Odoo warehouse quantities.",
    )
    vendor_stock_count = fields.Integer(
        string='Vendor Stock Location Count',
        compute='_compute_total_vendor_stock_qty',
        store=True,
    )

    _vendor_code_uniq = models.Constraint(
        'unique(vendor_id, vendor_code, company_id)',
        'This vendor product code already exists for this vendor!',
    )

    @api.depends('stock_ids.quantity_product_uom')
    def _compute_total_vendor_stock_qty(self):
        for rec in self:
            rec.total_vendor_stock_qty = sum(rec.stock_ids.mapped('quantity_product_uom'))
            rec.vendor_stock_count = len(rec.stock_ids)

    def action_open_vendor_stock(self):
        self.ensure_one()
        return {
            'name': 'Vendor Stock',
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.stock',
            'view_mode': 'list,form',
            'domain': [('vendor_product_id', '=', self.id)],
            'context': {
                'default_vendor_product_id': self.id,
                'default_vendor_id': self.vendor_id.id,
            },
        }

    @api.constrains('vendor_id')
    def _check_vendor_is_supplier(self):
        for rec in self:
            if rec.vendor_id and rec.vendor_id.supplier_rank <= 0:
                raise ValidationError(
                    "The selected contact is not marked as a Vendor. "
                    "Please choose a contact with supplier rank > 0, "
                    "or set them as a Vendor first."
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_catalog_notify'):
            for record in records:
                record._notify_catalog_event(
                    'inom_vender_product_management.mt_vendor_product_new',
                    'inom_vender_product_management.mt_partner_vendor_product_new',
                    "New vendor product added: %s" % record.vendor_product_name,
                )
        return records

    def write(self, vals):
        price_changing = 'vendor_price' in vals and not self.env.context.get('skip_catalog_notify')
        old_prices = {rec.id: rec.vendor_price for rec in self} if price_changing else {}
        res = super().write(vals)
        if price_changing:
            for rec in self:
                if old_prices.get(rec.id) != rec.vendor_price:
                    rec._notify_catalog_event(
                        'inom_vender_product_management.mt_vendor_product_price_update',
                        'inom_vender_product_management.mt_partner_vendor_product_price_update',
                        "New price for %s: %s %s" % (
                            rec.vendor_product_name, rec.vendor_price, rec.currency_id.name,
                        ),
                    )
        return res

    def _notify_catalog_event(self, subtype_xmlid, partner_subtype_xmlid, body):
        """Post one message on this vendor product and a matching one on
        the vendor's own contact, so a buyer can follow either and only
        the subtypes they picked in "Edit Subscription" notify them."""
        self.ensure_one()
        self.message_post(body=body, subtype_xmlid=subtype_xmlid)
        if self.vendor_id:
            self.vendor_id.message_post(body=body, subtype_xmlid=partner_subtype_xmlid)

    @api.depends('vendor_product_name', 'vendor_code', 'vendor_id.name')
    def _compute_display_name(self):
        for rec in self:
            name = rec.vendor_product_name or ''
            if rec.vendor_code:
                name = f"[{rec.vendor_code}] {name}"
            if rec.vendor_id:
                name = f"{rec.vendor_id.name} - {name}"
            rec.display_name = name
