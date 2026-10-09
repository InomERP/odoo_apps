# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    inom_branch_id = fields.Many2one(
        comodel_name="inom.branch", string="Branch",
        related="move_id.inom_branch_id", store=True, index=True, readonly=True,
        help="Branch taken from the parent journal entry.",
    )
