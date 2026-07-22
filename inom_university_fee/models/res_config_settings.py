# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fee_journal_id = fields.Many2one(
        related="company_id.fee_journal_id", readonly=False
    )
    fee_late_fee_rate = fields.Monetary(
        related="company_id.fee_late_fee_rate", readonly=False
    )
    fee_late_fee_cap = fields.Monetary(
        related="company_id.fee_late_fee_cap", readonly=False
    )
    fee_defaulter_days = fields.Integer(
        related="company_id.fee_defaulter_days", readonly=False
    )
    fee_refund_threshold = fields.Monetary(
        related="company_id.fee_refund_threshold", readonly=False
    )
