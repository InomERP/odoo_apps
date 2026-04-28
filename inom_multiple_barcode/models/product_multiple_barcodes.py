from odoo import fields, models


class ProductMultiBarcode(models.Model):
    """Creating multiple barcode for products"""
    _name = 'product.multiple.barcodes'
    _description = 'Product Multiple Barcodes'
    _rec_name = 'product_multi_barcode'

    product_multi_barcode = fields.Char(string="Barcode",
                                        help="Provide alternate barcodes for "
                                             "the product")
    product_id = fields.Many2one('product.product', string="Product Variant",
                                 help="This will be the Product "
                                      "variants")
    product_template_id = fields.Many2one('product.template', string="Product",
                                          help="This will be the products")
    _sql_constraints = [
        ('field_unique', 'unique(product_multi_barcode)',
         'Existing barcode is not allowed !'),]

    def get_barcode_val(self, product):
        return self.product_multi_barcode, product
