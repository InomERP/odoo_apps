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

        for d in domain:
            if isinstance(d, (list, tuple)) and d[0] == 'barcode':
                barcode = d[2]
                rec = self.env['product.multiple.barcodes'].search(
                    [('product_multi_barcode', '=', barcode)],
                    limit=1
                )
                if rec:
                    return rec.product_id.id
        return False

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        product_id = self._check_multi_barcode(domain)
        if product_id:
            domain = [('id', '=', product_id)]

        return super().search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order
        )

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.multi_barcode_ids:
            res.multi_barcode_ids.write({
                'product_template_id': res.product_tmpl_id.id
            })
        return res

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.multi_barcode_ids:
                rec.multi_barcode_ids.write({
                    'product_template_id': rec.product_tmpl_id.id
                })
        return res

