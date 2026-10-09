from odoo import api, fields, models


class ProductMultiBarcode(models.Model):
    _name = 'product.multiple.barcodes'
    _description = 'Product Multiple Barcodes'
    _rec_name = 'product_multi_barcode'

    product_multi_barcode = fields.Char(string="Barcode")
    product_id = fields.Many2one(
        'product.product',
        string="Product Variant",
        compute='_compute_product_id',
        store=True,
        readonly=False,
        index=True,
        ondelete='set null',
    )
    product_template_id = fields.Many2one(
        'product.template',
        string="Product",
        compute='_compute_product_template_id',
        store=True,
        readonly=False,
        index=True,
        ondelete='cascade',
    )

    _field_unique = models.Constraint(
        'unique(product_multi_barcode)',
        'Existing barcode is not allowed !',
    )

    @api.depends('product_template_id', 'product_template_id.product_variant_ids')
    def _compute_product_id(self):
        # Barcodes entered on a template point to its variant; re-point them
        # when that variant is removed or replaced (e.g. variants regenerated).
        for barcode in self:
            template = barcode.product_template_id
            if template and barcode.product_id not in template.product_variant_ids:
                barcode.product_id = template.product_variant_id
            else:
                barcode.product_id = barcode.product_id

    @api.depends('product_id')
    def _compute_product_template_id(self):
        for barcode in self:
            barcode.product_template_id = barcode.product_id.product_tmpl_id or barcode.product_template_id
