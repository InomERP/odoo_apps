# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    inom_default_branch_id = fields.Many2one(
        comodel_name="inom.branch", string="Default Branch",
        domain="[('company_id', 'in', company_ids)]",
        help="Branch automatically applied to new accounting documents "
             "created by this user.",
    )
    inom_allowed_branch_ids = fields.Many2many(
        comodel_name="inom.branch", relation="inom_branch_allowed_users_rel",
        column1="user_id", column2="branch_id",
        string="Allowed Branches",
        help="Branches whose records this user is allowed to access.",
    )
    inom_branch_filter_ids = fields.Many2many(
        comodel_name="inom.branch", string="Branch Access Filter",
        compute="_compute_inom_branch_filter_ids",
        help="Technical field used by record rules. Restricted branch users "
             "resolve to their allowed branches; everyone else resolves to all "
             "branches so they stay unrestricted.",
    )

    @api.depends("inom_allowed_branch_ids", "group_ids")
    def _compute_inom_branch_filter_ids(self):
        all_branches = self.env["inom.branch"].sudo().search([])
        for user in self:
            is_user = user.has_group(
                "inom_multibranch_invoice.group_inom_branch_user")
            is_manager = user.has_group(
                "inom_multibranch_invoice.group_inom_branch_manager")
            if is_user and not is_manager:
                user.inom_branch_filter_ids = user.inom_allowed_branch_ids
            else:
                user.inom_branch_filter_ids = all_branches

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "inom_default_branch_id", "inom_allowed_branch_ids",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["inom_default_branch_id"]

    @api.onchange("inom_allowed_branch_ids")
    def _onchange_inom_allowed_branch_ids(self):
        """Keep the default branch consistent with the allowed list."""
        for user in self:
            allowed = user.inom_allowed_branch_ids
            if user.inom_default_branch_id and user.inom_default_branch_id not in allowed:
                user.inom_default_branch_id = allowed[:1]