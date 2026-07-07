# -*- coding: utf-8 -*-
from odoo import fields, models


class InomSalesTarget(models.Model):
    """Sales revenue target per sales team and period.

    Phase 1 skeleton: fields only, as defined in SRS section 16.2. This model
    will later feed the Revenue Target Achievement widget (W-11). No business
    logic, computation or aggregation is implemented in this phase.
    """

    _name = "inom.sales.target"
    _description = "Sales Revenue Target"
    _rec_name = "team_id"

    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        help="The sales team this revenue target applies to.",
    )
    period_start = fields.Date(
        string="Period Start",
        help="Start date of the target window.",
    )
    period_end = fields.Date(
        string="Period End",
        help="End date of the target window.",
    )
    target_amount = fields.Monetary(
        string="Target Amount",
        currency_field="currency_id",
        help="Revenue goal for the team in the target period (company currency).",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
