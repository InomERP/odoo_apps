# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CreateRoleFromUserWizard(models.TransientModel):
    _name = 'create.role.from.user.wizard'
    _description = 'Create Role from Existing User'

    source_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Source User',
        required=True,
        readonly=True,
        help='The user whose current permissions will be copied into the new role.',
    )
    role_name = fields.Char(
        string='Role Name',
        required=True,
        help='Name for the new role (e.g. "Senior Accountant").',
    )
    description = fields.Text(
        string='Description',
    )
    group_ids = fields.Many2many(
        comodel_name='res.groups',
        string='Groups to Copy',
        readonly=True,
        help='These are the current groups of the selected user. All will be copied into the new role.',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            user = self.env['res.users'].browse(active_id)
            res['source_user_id'] = user.id
            self.env.cr.execute(
                "SELECT gid FROM res_groups_users_rel WHERE uid = %s",
                (user.id,)
            )
            rows = self.env.cr.fetchall()
            res['group_ids'] = [(6, 0, [r[0] for r in rows])] if rows else [(6, 0, [])]
        return res

    def action_create_role(self):
        """Create a new security.role from this wizard and open it."""
        self.ensure_one()
        role = self.env['security.role'].create({
            'name': self.role_name,
            'description': self.description or False,
            'source_user_id': self.source_user_id.id,
            'group_ids': [(6, 0, self.group_ids.ids)],
        })
        return {
            'name': 'Role: %s' % role.name,
            'type': 'ir.actions.act_window',
            'res_model': 'security.role',
            'view_mode': 'form',
            'res_id': role.id,
            'target': 'current',
        }