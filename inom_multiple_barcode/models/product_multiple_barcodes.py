from odoo import fields, models


class ProductMultiBarcode(models.Model):
    _name = 'product.multiple.barcodes'
    _description = 'Product Multiple Barcodes'
    _rec_name = 'product_multi_barcode'

    product_multi_barcode = fields.Char(string="Barcode")
    product_id = fields.Many2one('product.product', string="Product Variant")
    product_template_id = fields.Many2one('product.template', string="Product")

    _sql_constraints = [
        ('field_unique', 'unique(product_multi_barcode)',
         'Existing barcode is not allowed !'),
    ]