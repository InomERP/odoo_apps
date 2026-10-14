# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    material_requisition_id = fields.Many2one(
        'material.requisition',
        string='Material Requisition',
        copy=False,
    )