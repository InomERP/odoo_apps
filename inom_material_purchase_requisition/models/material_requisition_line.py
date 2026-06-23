# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MaterialRequisitionLine(models.Model):
    _name = 'material.requisition.line'
    _description = 'Material Purchase Requisition Line'

    requisition_id = fields.Many2one(
        'material.requisition',
        string='Requisition',
        ondelete='cascade',
    )

    # ---- Feature 2: requisition line fields ----
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    product_uom_qty = fields.Float(
        string='Quantity',
        default=1.0,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
    )
    description = fields.Text(
        string='Description',
    )

    # ---- Feature 15: requisition action + vendor ----
    requisition_action = fields.Selection(
        [
            ('purchase_order', 'Purchase Order'),
            ('internal_picking', 'Internal Picking'),
        ],
        string='Requisition Action',
        default='purchase_order',
        required=True,
        help='Purchase Order: buy the product from a vendor.\n'
             'Internal Picking: transfer the product from internal stock.',
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain="[('supplier_rank', '>', 0)]",
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_id
                if not line.description:
                    line.description = line.product_id.display_name
                seller = line.product_id.seller_ids[:1]
                if seller and not line.vendor_id:
                    line.vendor_id = seller.partner_id