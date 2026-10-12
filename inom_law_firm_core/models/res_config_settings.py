# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    law_default_branch_id = fields.Many2one(
        related="company_id.law_default_branch_id",
        string="Default Branch",
        readonly=False,
        help="Default branch used across the INOM Law Firm suite.",
    )
