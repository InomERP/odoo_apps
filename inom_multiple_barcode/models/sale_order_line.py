from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    scan_barcode = fields.Char(string='Product Barcode')

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)

        
        res['scan_barcode'] = self.scan_barcode

        return res

    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        if self.scan_barcode:
            product = self.env['product.multiple.barcodes'].search(
                [('product_multi_barcode', '=', self.scan_barcode)],
                limit=1
            )
            if product:
                self.product_id = product.product_id