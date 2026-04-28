from odoo import api, fields, models



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    scan_barcode = fields.Char(
        string='Product Barcode',
        compute="_compute_scan_barcode",
        store=True
    )

    @api.depends('purchase_line_id')
    def _compute_scan_barcode(self):
        for line in self:
            if line.purchase_line_id:
                line.scan_barcode = line.purchase_line_id.scan_barcode
            else:
                line.scan_barcode = False

    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        if self.scan_barcode:
            product = self.env['product.multiple.barcodes'].search(
                [('product_multi_barcode', '=', self.scan_barcode)],
                limit=1
            )
            if product:
                self.product_id = product.product_id














