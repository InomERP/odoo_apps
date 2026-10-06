# -*- coding: utf-8 -*-
from odoo import fields, models, _, Command


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    inom_sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Sale Order Line',
        copy=False,
        index='btree_not_null',
        help='Sale order line that requested this manufacturing order through the selected BoM.',
    )


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        """Confirm the order and ensure a Manufacturing Order exists for
        every line that has a Manufacture (normal) BoM selected.

        Odoo 20 uses stock.reference for Sale Order <-> Manufacturing Order
        linkage. We keep the v19 behaviour by creating an MO when a selected
        normal BoM would otherwise not create one automatically.
        """
        res = super()._action_confirm()
        self._inom_generate_bom_manufacturing_orders()
        return res

    def _inom_generate_bom_manufacturing_orders(self):
        """Create one draft Manufacturing Order per eligible sale line.

        The selected BoM is always used. Existing MOs created for the same
        sale line are left untouched, preventing duplicates on reprocessing.
        """
        production_model = self.env['mrp.production'].sudo()

        for order in self:
            # sale_stock creates this reference during procurement launch.
            references = order.stock_reference_ids
            if not references:
                # Defensive fallback for unusual/manual confirmation flows.
                reference = self.env['stock.reference'].sudo().create({
                    'name': order.name,
                    'sale_ids': [Command.link(order.id)],
                })
                references = reference

            created = production_model.browse()

            for line in order.order_line:
                if not line._inom_needs_manual_manufacturing_order():
                    continue

                bom = line.bom_id
                picking_type = bom.picking_type_id
                if not picking_type:
                    warehouse = line.sudo().warehouse_id
                    picking_type = warehouse.manu_type_id if warehouse else self.env['stock.picking.type'].search([
                        ('code', '=', 'mrp_operation'),
                        ('warehouse_id.company_id', '=', order.company_id.id),
                    ], limit=1)

                if not picking_type:
                    continue

                mo_vals = {
                    'origin': order.name,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_uom_id._compute_quantity(
                        line.product_uom_qty, bom.uom_id
                    ),
                    'uom_id': bom.uom_id.id,
                    'bom_id': bom.id,
                    'picking_type_id': picking_type.id,
                    'company_id': order.company_id.id,
                    'reference_ids': [Command.set(references.ids)],
                    'inom_sale_line_id': line.id,
                    'user_id': order.user_id.id or self.env.user.id,
                }

                # Use the same source/destination locations Odoo 20's
                # manufacturing stock rule uses for this operation type.
                mo_vals.update({
                    'location_src_id': picking_type.default_location_src_id.id,
                    'location_dest_id': (
                        picking_type.default_location_dest_id.id
                        or line.sudo().warehouse_id.lot_stock_id.id
                    ),
                })

                mo = production_model.create(mo_vals)
                created |= mo

            if created:
                # reference_ids makes the native Odoo 20 Manufacturing smart
                # button include these MOs through stock_reference_ids.
                order.message_post(
                    body=_(
                        "Manufacturing Order(s) created from the selected "
                        "Bill of Material: %s",
                        ", ".join(created.mapped('name')),
                    )
                )
                order.invalidate_recordset(
                    ['mrp_production_ids', 'mrp_production_count']
                )


