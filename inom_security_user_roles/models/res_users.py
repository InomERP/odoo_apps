# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    role_ids = fields.Many2many(
        comodel_name='security.role',
        relation='inom_security_role_users_rel',
        column1='user_id',
        column2='role_id',
        string='Roles',
        help='Roles assigned to this user. The groups from every assigned '
             'role are granted to the user automatically.',
    )

    # ─── create / write ──────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._apply_role_groups()
        return users

    def write(self, vals):
        old_roles_per_user = {}
        if 'role_ids' in vals and not self.env.context.get('_syncing_roles'):
            old_roles_per_user = {u.id: u.role_ids for u in self}

        res = super().write(vals)

        if 'role_ids' in vals and not self.env.context.get('_syncing_roles'):
            for user in self:
                old_roles = old_roles_per_user.get(user.id) or self.env['security.role']
                removed_roles = old_roles - user.role_ids
                user._apply_role_groups()
                if removed_roles:
                    user._remove_groups_from_roles(removed_roles)
        return res

    # ─── core sync helpers (Direct SQL — Odoo 19 compatible) ─────────────────

    def _apply_role_groups(self):
        """Add the union of every assigned role's group_ids to each user
        using direct SQL to avoid field name issues in Odoo 19."""
        if self.env.context.get('_syncing_roles'):
            return
        for user in self:
            role_groups = user.role_ids.mapped('group_ids')
            if not role_groups:
                continue
            # Direct SQL insert into the groups-users relation table
            for group in role_groups:
                self.env.cr.execute(
                    """
                    INSERT INTO res_groups_users_rel (gid, uid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (group.id, user.id)
                )
            if 'notification_type' in self._fields:
                for role in user.role_ids:
                    if role.notify_by_odoo:
                        self.env.cr.execute(
                            """
                            UPDATE res_users
                            SET notification_type = 'inbox'
                            WHERE id = %s
                            """,
                            (user.id,)
                        )
                        break
            # Invalidate cache so Odoo picks up the changes
            user.invalidate_recordset()

    def _remove_groups_from_roles(self, removed_roles):
        """Remove groups that came from removed_roles, but keep any group
        still granted by one of the user's remaining roles."""
        if self.env.context.get('_syncing_roles'):
            return
        for user in self:
            removed_group_ids = removed_roles.mapped('group_ids')
            kept_group_ids = user.role_ids.mapped('group_ids')
            to_remove = removed_group_ids - kept_group_ids
            if not to_remove:
                continue
            remove_ids = to_remove.ids
            self.env.cr.execute(
                """
                DELETE FROM res_groups_users_rel
                WHERE uid = %s AND gid = ANY(%s)
                """,
                (user.id, remove_ids)
            )
            user.invalidate_recordset()

    def _get_manually_added_groups(self):

        self.ensure_one()
        if not self.role_ids:
            return self.env['res.groups']


        self.env.cr.execute(
            "SELECT gid FROM res_groups_users_rel WHERE uid = %s",
            (self.id,)
        )
        current_gids = {r[0] for r in self.env.cr.fetchall()}

        role_gids = set(self.role_ids.mapped('group_ids').ids)

        manual_gids = current_gids - role_gids
        if not manual_gids:
            return self.env['res.groups']

        return self.env['res.groups'].browse(list(manual_gids))

    def action_warn_manual_groups(self):

        self.ensure_one()
        manual_groups = self._get_manually_added_groups()
        if not manual_groups:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Manual Groups',
                    'message': 'All user groups are assigned through roles. No manual group assignments detected. Safe to proceed.',
                    'type': 'success',
                    'sticky': False,
                },
            }
        group_names = ', '.join(
            g.name.get('en_US', str(g.name)) if isinstance(g.name, dict) else str(g.name)
            for g in manual_groups
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Warning: Manually Added Groups',
                'message': (
                        f'The following groups have been assigned manually and may be cleared during the next role synchronization:\n'
                        f'{group_names}\n\n'
                        f'Please add these groups to a role to ensure they remain assigned.'
                    ),
                'type': 'warning',
                'sticky': True,
            },
        }

    def action_open_create_role_wizard(self):
        """Feature 3: Open wizard to create a role from this user's permissions."""
        self.ensure_one()
        return {
            'name': 'Create Role from User: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'create.role.from.user.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
            },
        }


class SecurityRoleScheduler(models.Model):
    _name = 'security.role.scheduler'
    _description = 'Security Role Scheduler'

    def action_apply_temporary_rules(self):

        today = fields.Date.today()
        all_roles = self.env['security.role'].search([])

        for role in all_roles:
            for rule in role.temporary_rule_ids:
                is_active = rule.date_from <= today <= rule.date_to
                user = rule.user_id

                if rule.rule_type == 'block':
                    if is_active and not rule.is_applied:
                        self.env.cr.execute(
                            "SELECT gid FROM res_groups_users_rel WHERE uid = %s",
                            (user.id,)
                        )
                        current_group_ids = [r[0] for r in self.env.cr.fetchall()]


                        other_role_groups = self.env['security.role'].search([
                            ('user_ids', 'in', user.id),
                            ('id', '!=', role.id),
                        ]).mapped('group_ids').ids

                        to_remove = [
                            gid for gid in role.group_ids.ids
                            if gid in current_group_ids and gid not in other_role_groups
                        ]

                        if to_remove:
                            self.env.cr.execute(
                                """
                                DELETE FROM res_groups_users_rel
                                WHERE uid = %s AND gid = ANY(%s)
                                """,
                                (user.id, to_remove)
                            )


                        self.env.cr.execute(
                            """
                            UPDATE security_role_temporary_rule
                            SET is_applied = TRUE
                            WHERE id = %s
                            """,
                            (rule.id,)
                        )
                        user.invalidate_recordset()

                    elif not is_active and rule.is_applied:
                        for group in role.group_ids:
                            self.env.cr.execute(
                                """
                                INSERT INTO res_groups_users_rel (gid, uid)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                                """,
                                (group.id, user.id)
                            )

                        self.env.cr.execute(
                            """
                            UPDATE security_role_temporary_rule
                            SET is_applied = FALSE
                            WHERE id = %s
                            """,
                            (rule.id,)
                        )
                        user.invalidate_recordset()

                elif rule.rule_type == 'activate':
                    if is_active and not rule.is_applied:
                        for group in role.group_ids:
                            self.env.cr.execute(
                                """
                                INSERT INTO res_groups_users_rel (gid, uid)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                                """,
                                (group.id, user.id)
                            )
                        self.env.cr.execute(
                            """
                            UPDATE security_role_temporary_rule
                            SET is_applied = TRUE
                            WHERE id = %s
                            """,
                            (rule.id,)
                        )
                        user.invalidate_recordset()

                    elif not is_active and rule.is_applied:
                        other_role_groups = self.env['security.role'].search([
                            ('user_ids', 'in', user.id),
                        ]).mapped('group_ids').ids

                        to_remove = [
                            gid for gid in role.group_ids.ids
                            if gid not in other_role_groups
                        ]

                        if to_remove:
                            self.env.cr.execute(
                                """
                                DELETE FROM res_groups_users_rel
                                WHERE uid = %s AND gid = ANY(%s)
                                """,
                                (user.id, to_remove)
                            )

                        self.env.cr.execute(
                            """
                            UPDATE security_role_temporary_rule
                            SET is_applied = FALSE
                            WHERE id = %s
                            """,
                            (rule.id,)
                        )
                        user.invalidate_recordset()