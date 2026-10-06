# -*- coding: utf-8 -*-
from odoo import api, models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_management_permission = fields.Boolean(
        string='POS Management Permission',
        compute='_compute_pos_management_permission',
        inverse='_inverse_pos_management_permission',
        help="Enable to allow this user to manage POS access rights. "
             "When enabled, the user is added to the 'POS Access Manager' group "
             "and can manage rules from Point of Sale > Configuration > POS Access Rights.",
    )
    pos_access_rights_ids = fields.One2many(
        'pos.access.rights',
        'user_id',
        string='POS Access Rights',
    )

    @api.depends('group_ids')
    def _compute_pos_management_permission(self):
        group = self.env.ref('inom_pos_access_management.group_pos_access_manager', raise_if_not_found=False)
        for user in self:
            user.pos_management_permission = bool(group) and group in user.all_group_ids

    def _inverse_pos_management_permission(self):
        group = self.env.ref('inom_pos_access_management.group_pos_access_manager', raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.pos_management_permission:
                user.group_ids = [fields.Command.link(group.id)]
            else:
                user.group_ids = [fields.Command.unlink(group.id)]
