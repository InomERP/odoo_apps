from odoo import api, fields, models


class PurchaseOrderLines(models.Model):
    _inherit = "purchase.order.line"

    scan_barcode = fields.Char(string='Product Barcode')

    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        if self.scan_barcode:
            product = self.env['product.multiple.barcodes'].search(
                [('product_multi_barcode', '=', self.scan_barcode)],
                limit=1
            )
            if product:
                self.product_id = product.product_id