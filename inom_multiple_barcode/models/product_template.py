from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    template_multi_barcode_ids = fields.One2many(
        'product.multiple.barcodes',
        'product_template_id',
        string='Multi Barcodes',
        help="Multi barcode for product template")

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if self.template_multi_barcode_ids:
            self.template_multi_barcode_ids.update({
                'product_id': self.product_variant_id.id
            })
        return res

    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        res.template_multi_barcode_ids.update({
            'product_id': res.product_variant_id.id
        })
        return res
