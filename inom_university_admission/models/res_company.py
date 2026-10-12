# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    univ_applicant_prefix = fields.Char(
        string="Applicant Prefix",
        default="APP",
        help="Campus-aware prefix prepended to the auto-generated application "
             "number.",
    )
