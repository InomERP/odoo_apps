# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Odoo 17's ``sale_mrp`` does not link a Manufacturing Order to its origin
    # Sale Order line. This field provides that link so the module can attach
    # the MO created from a Sale Order line and surface it on the Sale Order.
    sale_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Origin Sale Order Line',
        copy=False,
        index='btree_not_null',
    )
