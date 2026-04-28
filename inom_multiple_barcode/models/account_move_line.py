from odoo import api, fields, models


class AccountMoveLine(models.Model):
    """ Inherits Account.move.line for scanning multi barcode """
    _inherit = 'account.move.line'

    scan_barcode = fields.Char(string='Product Barcode',
                               compute="_compute_scan_barcode",
                               inverse="_inverse_scan_barcode", store=True,
                               help="You can scan the barcode here")

    @api.depends('purchase_line_id')
    def _compute_scan_barcode(self):
        """ For updating the Product Barcode field in move line while it's
        generating from a Purchase order. """
        for line in self:
            if line.purchase_line_id:
                line.scan_barcode = line.purchase_line_id.scan_barcode

    def _inverse_scan_barcode(self):
        """Inverse function for scan_barcode"""
        for account in self:
            account.scan_barcode = account.scan_barcode

    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        """ For getting the scanned barcode product """
        if self.scan_barcode:
            product = self.env['product.multiple.barcodes'].search(
                [('product_multi_barcode', '=', self.scan_barcode)])
            self.product_id = product.product_id.id
