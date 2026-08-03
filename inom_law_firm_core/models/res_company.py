# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    law_default_branch_id = fields.Many2one(
        "law.branch",
        string="Default Law Firm Branch",
        help="Default branch used when creating law firm records for this company.",
    )
