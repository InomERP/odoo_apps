# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    adjust_settings_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Adjustment Currency',
    )
    adjust_approval_require_all = fields.Boolean(
        related='company_id.adjust_approval_require_all',
        readonly=False,
    )
    adjust_approval_qty_threshold = fields.Float(
        related='company_id.adjust_approval_qty_threshold',
        readonly=False,
    )
    adjust_approval_value_threshold = fields.Monetary(
        related='company_id.adjust_approval_value_threshold',
        readonly=False,
        currency_field='adjust_settings_currency_id',
    )
