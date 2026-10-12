# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    fee_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Fee Sales Journal",
        domain="[('type', '=', 'sale'), ('company_id', '=', id)]",
        help="Journal used for fee invoices. Falls back to the first sales "
             "journal when empty.",
    )
    fee_late_fee_rate = fields.Monetary(
        string="Late Fee per Day",
        currency_field="currency_id",
        default=0.0,
        help="Flat amount accrued per overdue day.",
    )
    fee_late_fee_cap = fields.Monetary(
        string="Late Fee Cap",
        currency_field="currency_id",
        default=0.0,
        help="Maximum late fee that can accrue on a single invoice (0 = no cap).",
    )
    fee_defaulter_days = fields.Integer(
        string="Defaulter After (days)",
        default=60,
        help="Days overdue after which a student is flagged as a fee defaulter.",
    )
    fee_refund_threshold = fields.Monetary(
        string="Two-level Refund Threshold",
        currency_field="currency_id",
        default=25000.0,
        help="Refund requests above this amount require a second (registrar) "
             "approval.",
    )
