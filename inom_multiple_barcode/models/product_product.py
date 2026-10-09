from odoo import api, fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    multi_barcode_ids = fields.One2many(
        'product.multiple.barcodes',
        'product_id',
        string='Barcodes'
    )

    def _check_multi_barcode(self, domain):
        if not domain or not isinstance(domain, list):
            return False

        barcodes = [
            d[2] for d in domain
            if isinstance(d, (list, tuple)) and len(d) == 3
            and d[0] == 'barcode' and isinstance(d[2], str)
        ]
        if not barcodes:
            return False

        records = self.env['product.multiple.barcodes'].search(
            [('product_multi_barcode', 'in', barcodes)]
        )
        product_by_barcode = {
            rec.product_multi_barcode: rec.product_id.id for rec in records
        }
        return next(
            (product_by_barcode[b] for b in barcodes if product_by_barcode.get(b)),
            False
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        product_id = self._check_multi_barcode(domain)
        if product_id:
            domain = [('id', '=', product_id)]

        return super().search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order,
            **read_kwargs
        )
