# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    inom_warehouse_location_ids = fields.Many2many(
        comodel_name="stock.location",
        relation="inom_location_user_rel",
        column1="user_id",
        column2="location_id",
        string="Authorized Warehouse Locations",
        help="Locations this user is allowed to access. This is the same "
             "relation as the authorized users defined on each location, so "
             "editing it here or on the location form has the same effect.",
    )
