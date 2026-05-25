# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


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
    def get_pos_stock_by_location(self, product_ids, location_id=False, stock_type='on_hand'):

        if not product_ids:
            return []

        if location_id:

            self.env.cr.execute("""
                SELECT
                    pp.product_tmpl_id AS tmpl_id,
                    COALESCE(SUM(sq.quantity), 0) - COALESCE(SUM(sq.reserved_quantity), 0) AS qty_available,
                    COALESCE(SUM(sq.quantity), 0) AS qty_on_hand
                FROM stock_quant sq
                JOIN product_product pp ON pp.id = sq.product_id
                JOIN stock_location  sl ON sl.id = sq.location_id
                WHERE pp.product_tmpl_id = ANY(%s)
                  AND sl.usage  = 'internal'
                  AND sl.active = true
                  AND sl.parent_path LIKE (
                      SELECT parent_path || '%%'
                      FROM stock_location WHERE id = %s
                  )
                GROUP BY pp.product_tmpl_id
            """, (product_ids, location_id))
        else:
            self.env.cr.execute("""
                SELECT
                    pp.product_tmpl_id          AS tmpl_id,
                    COALESCE(SUM(sq.quantity), 0) - COALESCE(SUM(sq.reserved_quantity), 0)
                                                AS qty_available,
                    COALESCE(SUM(sq.quantity), 0) AS qty_on_hand
                FROM stock_quant sq
                JOIN product_product pp ON pp.id = sq.product_id
                JOIN stock_location   sl ON sl.id = sq.location_id
                WHERE pp.product_tmpl_id = ANY(%s)
                  AND sl.usage = 'internal'
                  AND sl.active = true
                GROUP BY pp.product_tmpl_id
            """, (product_ids,))

        rows = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}
        _logger.info("INOM stock SQL: %d templates, sample: %s",
                     len(rows), list(rows.items())[:4])

        result = []
        templates = self.browse(product_ids)
        for tmpl in templates:
            if tmpl.type == 'service':
                result.append({'id': tmpl.id, 'pos_qty': 0, 'virtual_available': 0})
                continue

            if tmpl.id in rows:

                qty_available, qty_on_hand = rows[tmpl.id]
            else:
                qty_available = 0.0
                qty_on_hand   = 0.0

            result.append({
                'id':               tmpl.id,
                'pos_qty':          float(qty_on_hand),    # JS on_hand path
                'virtual_available': float(qty_available),  # JS available path
            })

        return result