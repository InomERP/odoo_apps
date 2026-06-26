# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    bom_id = fields.Many2one(
        comodel_name='mrp.bom',
        string='Bill of Material',
        domain="[('id', 'in', allowed_bom_ids)]",
        help="Bill of Material to use for this product on this order line.\n"
             "- Manufacture BoM: the related Manufacturing Order is created "
             "with this exact BoM.\n"
             "- Kit BoM: the Delivery Order is built from the components of "
             "this exact Kit BoM.\n"
             "Only BoMs linked to the line product are proposed. If left "
             "empty, Odoo keeps its default behaviour.",
        ondelete='set null',
        index='btree_not_null',
        copy=True,
    )
    allowed_bom_ids = fields.Many2many(
        comodel_name='mrp.bom',
        string='Allowed Bills of Material',
        compute='_compute_allowed_bom_ids',
        help="Technical field listing the BoMs that may be selected for the "
             "current line product (used to filter the Bill of Material field).",
    )

    @api.depends('product_id', 'company_id')
    def _compute_allowed_bom_ids(self):
        """Compute the BoMs that are linked to the line product.

        A BoM is considered linked when it targets the exact product variant
        (``product_id``) or its product template (``product_id`` empty and
        matching ``product_tmpl_id``). Both Manufacture (normal) and Kit
        (phantom) BoMs are proposed.
        """
        bom_model = self.env['mrp.bom']
        for line in self:
            product = line.product_id
            if not product:
                line.allowed_bom_ids = bom_model
                continue
            company_ids = [False]
            if line.company_id:
                company_ids.append(line.company_id.id)
            line.allowed_bom_ids = bom_model.search([
                '|',
                ('product_id', '=', product.id),
                '&',
                ('product_id', '=', False),
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('company_id', 'in', company_ids),
            ])

    @api.onchange('product_id', 'product_template_id')
    def _onchange_product_reset_bom_id(self):
        """Clear the selected BoM when it no longer matches the line product."""
        for line in self:
            if line.bom_id and line.bom_id not in line.allowed_bom_ids:
                line.bom_id = False

    @api.constrains('bom_id', 'product_id')
    def _check_bom_matches_product(self):
        """Ensure a selected BoM really belongs to the line product."""
        for line in self:
            if not line.bom_id:
                continue
            bom = line.bom_id
            product = line.product_id
            if not product:
                raise ValidationError(_(
                    "A product must be set before selecting a Bill of Material."
                ))
            if bom.product_id:
                matches = bom.product_id == product
            else:
                matches = bom.product_tmpl_id == product.product_tmpl_id
            if not matches:
                raise ValidationError(_(
                    "The Bill of Material '%(bom)s' does not belong to the "
                    "product '%(product)s' on the order line.",
                    bom=bom.display_name,
                    product=product.display_name,
                ))

    def _prepare_procurement_values(self, group_id=False):
        """Carry the selected Manufacture BoM forward to the procurement.

        ``mrp``'s manufacture rule reads ``bom_id`` from the procurement values
        (see ``stock.rule._get_matching_bom``) and uses it as-is for the
        Manufacturing Order. Kit (phantom) BoMs are handled at the stock move
        explosion level instead, so only normal BoMs are injected here.
        """
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.bom_id and self.bom_id.type == 'normal':
            values['bom_id'] = self.bom_id
        return values

    def _inom_needs_manual_manufacturing_order(self):
        """Return True when this line should get a Manufacturing Order created
        by the module.

        Conditions: a real product line (not a section/note) with a positive
        quantity, a Manufacture (normal) BoM selected, and no Manufacturing
        Order already linked to the line (which would be the case when the
        product is replenished on order through the standard procurement chain).
        """
        self.ensure_one()
        if self.display_type or not self.product_id:
            return False
        bom = self.bom_id
        if not bom or bom.type != 'normal':
            return False
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure'
        )
        if float_compare(
                self.product_uom_qty, 0.0, precision_digits=precision) <= 0:
            return False
        existing = self.env['mrp.production'].sudo().search_count([
            ('sale_line_id', '=', self.id),
            ('state', '!=', 'cancel'),
        ])
        return not existing
