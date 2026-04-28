from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    template_multi_barcode_ids = fields.One2many(
        'product.multiple.barcodes',
        'product_template_id',
        string='Multi Barcodes'
    )

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.template_multi_barcode_ids:
                rec.template_multi_barcode_ids.write({
                    'product_id': rec.product_variant_id.id
                })
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.template_multi_barcode_ids:
            res.template_multi_barcode_ids.write({
                'product_id': res.product_variant_id.id
            })
        return res
