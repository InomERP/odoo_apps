# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    inom_authorized_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="inom_location_user_rel",
        column1="location_id",
        column2="user_id",
        string="Authorized Users",
        help="Users allowed to access this location. Leave this empty to keep "
             "the location global (accessible to everyone). Authorized users "
             "also gain access to all of this location's child locations.",
    )
    inom_effective_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="inom_location_effective_user_rel",
        column1="location_id",
        column2="user_id",
        string="Effective Authorized Users",
        compute="_compute_inom_effective_user_ids",
        store=True,
        recursive=True,
        help="Technical field. Aggregates the authorized users of this "
             "location together with the authorized users inherited from all "
             "of its parent locations. An empty value means the location is "
             "global.",
    )

    @api.depends(
        "inom_authorized_user_ids",
        "location_id",
        "location_id.inom_effective_user_ids",
    )
    def _compute_inom_effective_user_ids(self):
        for location in self:
            effective_users = location.inom_authorized_user_ids
            parent = location.location_id
            if parent:
                effective_users |= parent.inom_effective_user_ids
            location.inom_effective_user_ids = effective_users
