# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    adjust_approval_require_all = fields.Boolean(
        string='Require Approval for All Adjustments',
        help='When enabled, every inventory adjustment made by a non-approver '
             'requires approval, regardless of the configured thresholds.',
    )
    adjust_approval_qty_threshold = fields.Float(
        string='Quantity Difference Threshold',
        help='Adjustments whose absolute quantity difference is equal to or '
             'greater than this value require approval. Set to 0 to ignore.',
    )
    adjust_approval_value_threshold = fields.Monetary(
        string='Value Impact Threshold',
        currency_field='currency_id',
        help='Adjustments whose absolute value impact is equal to or greater '
             'than this amount require approval. Set to 0 to ignore.',
    )