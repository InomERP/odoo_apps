# -*- coding: utf-8 -*-
from odoo import models, _


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

        The Manufacturing smart button of ``sale_mrp`` already lists the
        Manufacturing Orders linked to a Sale Order line (``sale_line_id``), so
        no extra computation is required on this version.
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
