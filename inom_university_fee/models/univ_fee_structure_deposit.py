# -*- coding: utf-8 -*-
# Phase 4 - Configurable deposit percentage on the existing fee structure.
from odoo import fields, models


class UnivFeeStructure(models.Model):
    _inherit = "univ.fee.structure"

    deposit_percentage = fields.Float(
        string="Deposit %",
        default=50.0,
        help="Percentage of this structure's total tuition that an admitted "
        "applicant must pay as a deposit before enrolment. "
        "Deposit = Total x Deposit% / 100.",
    )
