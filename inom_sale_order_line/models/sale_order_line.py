from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_image = fields.Image(
        string="Image",
        compute="_compute_product_image",
        store=True,
        readonly=True
    )

    @api.depends('product_id', 'product_id.product_tmpl_id.image_1920')
    def _compute_product_image(self):
        for line in self:
            if line.product_id and line.product_id.product_tmpl_id.image_1920:
                line.product_image = line.product_id.product_tmpl_id.image_1920
            else:
                line.product_image = False

    @api.onchange('product_id')
    def _onchange_product_image(self):
        for line in self:
            if line.product_id and line.product_id.product_tmpl_id.image_1920:
                line.product_image = line.product_id.product_tmpl_id.image_1920
            else:
                line.product_image = False
