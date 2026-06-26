# -*- coding: utf-8 -*-
from odoo import api, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        """Confirm the order, then make sure a Manufacturing Order exists for
        every line that has a Manufacture (normal) BoM selected.

        Standard Odoo only chains a Sale Order to a Manufacturing Order when the
        product is replenished on order (MTO) or through a multi-step delivery.
        With a single Manufacture route and a one-step delivery, no MO is
        created automatically. This module guarantees the MO so the selected
        BoM is always produced and the Manufacturing smart button is shown.
        """
        res = super()._action_confirm()
        self._inom_generate_bom_manufacturing_orders()
        return res

    def _inom_generate_bom_manufacturing_orders(self):
        """Create a Manufacturing Order using the BoM chosen on each eligible
        Sale Order line, unless one already exists for that line."""
        production_model = self.env['mrp.production'].sudo()
        for order in self:
            created = production_model.browse()
            for line in order.order_line:
                if not line._inom_needs_manual_manufacturing_order():
                    continue
                created |= production_model.create(
                    order._inom_prepare_manufacturing_order_vals(line)
                )
            if created:
                # Refresh the computed Manufacturing button and give the user
                # a direct, visible link to the orders that were generated.
                order.invalidate_recordset(
                    ['mrp_production_ids', 'mrp_production_count']
                )
                links = ", ".join(
                    '<a href="#" data-oe-model="mrp.production" '
                    'data-oe-id="%s">%s</a>' % (mo.id, mo.name)
                    for mo in created
                )
                order.message_post(body=_(
                    "Manufacturing Order(s) created from the selected Bill of "
                    "Material: %s", links))

    def _inom_prepare_manufacturing_order_vals(self, line):
        """Build the values for the Manufacturing Order of a Sale Order line.

        The picking type, source/destination locations and component moves are
        recomputed automatically by ``mrp.production`` from ``bom_id``,
        ``product_id`` and ``product_qty``.
        """
        self.ensure_one()
        return {
            'origin': self.name,
            'product_id': line.product_id.id,
            'product_uom_id': line.product_uom.id,
            'product_qty': line.product_uom_qty,
            'bom_id': line.bom_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id or self.env.user.id,
            'sale_line_id': line.id,
        }

    @api.depends('procurement_group_id.stock_move_ids.created_production_id'
                 '.procurement_group_id.mrp_production_ids',
                 'order_line.bom_id', 'order_line.product_uom_qty')
    def _compute_mrp_production_ids(self):
        """Also surface Manufacturing Orders that this module created from a
        Sale Order line. Odoo 17's ``sale_mrp`` only links MOs through the
        procurement group, so the module-created MOs are added here."""
        super()._compute_mrp_production_ids()
        for sale in self:
            line_mos = self.env['mrp.production'].sudo().search([
                ('sale_line_id', 'in', sale.order_line.ids),
                ('state', '!=', 'cancel'),
            ])
            productions = sale.mrp_production_ids | line_mos
            sale.mrp_production_ids = productions
            sale.mrp_production_count = len(productions)
