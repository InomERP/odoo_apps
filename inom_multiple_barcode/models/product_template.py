from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    template_multi_barcode_ids = fields.One2many(
        'product.multiple.barcodes',
        'product_template_id',
        string='Multi Barcodes'
    )
