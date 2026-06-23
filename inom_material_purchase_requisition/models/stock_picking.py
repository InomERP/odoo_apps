# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    material_requisition_id = fields.Many2one(
        'material.requisition',
        string='Material Requisition',
        copy=False,
    )