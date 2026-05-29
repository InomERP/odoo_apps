# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_management_permission = fields.Boolean(
        string='POS Management Permission',
        help="Enable to allow this user to manage POS access rights. "
             "When enabled, the user can be assigned access rules from "
             "Point of Sale > Configuration > POS Access Rights.",
    )
    pos_access_rights_ids = fields.One2many(
        'pos.access.rights',
        'user_id',
        string='POS Access Rights',
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'pos_management_permission',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'pos_management_permission',
        ]
