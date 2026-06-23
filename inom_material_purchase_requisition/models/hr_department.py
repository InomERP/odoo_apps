# -*- coding: utf-8 -*-
from odoo import models, fields


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    # Feature 9: destination stock location used as the requisition target
    # when the employee has no specific location set.
    requisition_stock_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        domain="[('usage', 'in', ('internal', 'customer'))]",
        help='Default destination location for material requisitions '
             'of this department.',
    )