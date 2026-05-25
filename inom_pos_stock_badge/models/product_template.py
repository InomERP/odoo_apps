from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_qty = fields.Float(
        string='POS Stock Qty',
        compute='_compute_tmpl_pos_qty',
        store=True,
        digits='Product Unit of Measure',
    )

    @api.depends('qty_available', 'product_variant_ids.qty_available', 'virtual_available')
    def _compute_tmpl_pos_qty(self):
        for tmpl in self:
            if tmpl.type == 'service':
                tmpl.pos_qty = 0.0
            else:
                tmpl.pos_qty = tmpl.qty_available

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        for f in ('pos_qty', 'virtual_available', 'qty_available'):
            if f not in fields_list:
                fields_list.append(f)
        return fields_list

    @api.model
    def get_pos_stock_by_location(self, product_ids, location_id=False, stock_type='on_hand'):
        result = []
        if location_id:
            templates = self.with_context(location=location_id).browse(product_ids)
            for tmpl in templates:
                qty = tmpl.qty_available if stock_type == 'on_hand' else tmpl.virtual_available
                result.append({
                    'id': tmpl.id,
                    'pos_qty': qty,
                    'virtual_available': tmpl.virtual_available,
                })
        else:
            templates = self.browse(product_ids)
            for tmpl in templates:
                qty = tmpl.qty_available if stock_type == 'on_hand' else tmpl.virtual_available
                result.append({
                    'id': tmpl.id,
                    'pos_qty': qty,
                    'virtual_available': tmpl.virtual_available,
                })
        return result