# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_univ_applicant = fields.Boolean(
        string="University Applicant", default=False
    )
    univ_account_type = fields.Selection(
        selection=[
            ("student", "Student (Child)"),
            ("parent", "Parent"),
        ],
        string="Portal Account Type",
        help="Captured during portal self-registration to distinguish a "
             "student (child) account from a parent/guardian account.",
    )
    univ_applicant_ids = fields.One2many(
        comodel_name="univ.applicant",
        inverse_name="partner_id",
        string="Applications",
    )
