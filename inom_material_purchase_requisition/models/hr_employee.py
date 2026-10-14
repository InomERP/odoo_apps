# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Feature 8: destination stock location used as the requisition target.
    requisition_stock_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        domain="[('usage', 'in', ('internal', 'customer'))]",
        help='Default destination location for material requisitions '
             'submitted by this employee.',
    )