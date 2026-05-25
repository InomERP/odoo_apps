from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_qty = fields.Float(
        string='POS Stock Quantity',
        compute='_compute_tmpl_pos_qty',
        store=True,
    )

    @api.depends('product_variant_ids.qty_available')
    def _compute_tmpl_pos_qty(self):
        for tmpl in self:
            tmpl.pos_qty = sum(
                v.qty_available for v in tmpl.product_variant_ids
            )

    @api.model
    def get_pos_stock_by_location(self, product_ids=None, location_id=False, stock_type='on_hand'):
        try:
            if not product_ids:
                return []

            if location_id:
                loc_domain = [
                    ('id', 'child_of', int(location_id)),
                    ('usage', '=', 'internal'),
                ]
            else:
                loc_domain = [('usage', '=', 'internal')]

            valid_location_ids = self.env['stock.location'].search(loc_domain).ids
            _logger.info("[Inom] Valid locations: %s", valid_location_ids)

            if not valid_location_ids:
                fallback = self.env['stock.location'].search([
                    ('complete_name', 'ilike', 'WH/Stock'),
                    ('usage', '=', 'internal'),
                ], limit=1)
                valid_location_ids = [fallback.id] if fallback else []

            if not valid_location_ids:
                _logger.warning("[Inom] No internal locations found!")
                return []

            templates = self.browse(product_ids)
            tmpl_to_variants = {}
            all_variant_ids = []
            for tmpl in templates:
                vids = tmpl.product_variant_ids.ids
                tmpl_to_variants[tmpl.id] = vids
                all_variant_ids.extend(vids)

            if not all_variant_ids:
                return []

            quants = self.env['stock.quant'].search_read(
                [
                    ('product_id', 'in', all_variant_ids),
                    ('location_id', 'in', valid_location_ids),
                ],
                ['product_id', 'quantity', 'reserved_quantity'],
            )
            _logger.info("[Inom] Quants found: %s", len(quants))

            variant_to_tmpl = {}
            for tmpl_id, vids in tmpl_to_variants.items():
                for vid in vids:
                    variant_to_tmpl[vid] = tmpl_id

            tmpl_on_hand = {}
            tmpl_reserved = {}
            for q in quants:
                vid = q['product_id'][0]
                tid = variant_to_tmpl.get(vid)
                if tid is None:
                    continue
                tmpl_on_hand[tid] = tmpl_on_hand.get(tid, 0.0) + q['quantity']
                tmpl_reserved[tid] = tmpl_reserved.get(tid, 0.0) + q['reserved_quantity']

            result = []
            for tmpl_id in product_ids:
                on_hand = tmpl_on_hand.get(tmpl_id, 0.0)
                reserved = tmpl_reserved.get(tmpl_id, 0.0)
                available = on_hand - reserved

                if stock_type == 'available':
                    pos_qty = available
                    virtual_available = available
                else:
                    pos_qty = on_hand
                    virtual_available = available

                result.append({
                    'id': tmpl_id,
                    'pos_qty': pos_qty,
                    'virtual_available': virtual_available,
                })

            _logger.info("[Inom] Returning %s products", len(result))
            return result

        except Exception as e:
            _logger.error("[Inom] get_pos_stock_by_location error: %s", str(e))
            return []