from odoo import models, fields, api


class SecurityRole(models.Model):
    _name = 'security.role'
    _description = 'Security Role'
    _order = 'name'

    name = fields.Char(
        string='Role Name',
        required=True,
        translate=True,
    )
    description = fields.Text(
        string='Description',
        translate=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    group_ids = fields.Many2many(
        comodel_name='res.groups',
        relation='inom_security_role_groups_rel',
        column1='role_id',
        column2='group_id',
        string='Groups / Permissions',
        help='Every Odoo security group listed here will be granted to '
             'users assigned this role.',
    )
    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='inom_security_role_users_rel',
        column1='role_id',
        column2='user_id',
        string='Users',
        help='Users who have this role assigned.',
    )
    user_count = fields.Integer(
        string='Users Count',
        compute='_compute_counts',
    )
    group_count = fields.Integer(
        string='Groups Count',
        compute='_compute_counts',
    )
    source_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Copy Groups from User',
        help='Select an existing user to copy all their current groups into this role.',
    )
    temporary_rule_ids = fields.One2many(
        comodel_name='security.role.temporary.rule',
        inverse_name='role_id',
        string='Temporary Rules',
    )

    notify_by_odoo = fields.Boolean(
        string='Receive notifications in Odoo',
        default=False,
        help='Enable this option if all users assigned to '
             'this role should receive Odoo notifications in their inbox instead of by '
             'email. When the role is assigned or updated, users\' notification preference '
             'will be automatically set to "Inbox".'
    )


    _TECH_CATEGORY_XMLIDS = [
        'base.module_category_hidden',
        'base.module_category_usability',
        'base.module_category_extra',
        'base.module_category_hidden_extra_rights',
    ]

    show_technical_groups = fields.Boolean(
        string='Show Technical Groups',
        compute='_compute_show_technical_groups',
    )
    visible_group_ids = fields.Many2many(
        comodel_name='res.groups',
        string='Selectable Groups',
        compute='_compute_visible_group_ids',
        help='Domain used for the group_ids field. Technical groups are included '
             'or excluded based on the current settings and whether Developer Mode is enabled.'
    )

    def _get_technical_category_ids(self):
        ids = []
        for xmlid in self._TECH_CATEGORY_XMLIDS:
            cat = self.env.ref(xmlid, raise_if_not_found=False)
            if cat:
                ids.append(cat.id)
        return ids

    @api.depends_context('uid')
    def _compute_show_technical_groups(self):
        setting_on = self.env['ir.config_parameter'].sudo().get_bool(
            'inom_security_user_roles.show_technical_user_groups_without_dev_mode'
        )
        is_dev = self.env.user.has_group('base.group_no_one')
        show = setting_on or is_dev
        for role in self:
            role.show_technical_groups = show

    @api.depends_context('uid')
    def _compute_visible_group_ids(self):
        Groups = self.env['res.groups']
        setting_on = self.env['ir.config_parameter'].sudo().get_bool(
            'inom_security_user_roles.show_technical_user_groups_without_dev_mode'
        )
        is_dev = self.env.user.has_group('base.group_no_one')

        if setting_on or is_dev:

            visible = Groups.search([])
        else:

            TECHNICAL_XMLIDS = [
                'base.group_no_one',  # Technical Features
                'base.group_sanitize_override',  # Bypass HTML Field Sanitize
                'mail.group_mail_template_editor',  # Mail Template Editor
                'base.group_multi_currency',  # Multi Currencies
                'base.group_multi_company',  # Multi Companies
            ]
            hidden_ids = []
            for xmlid in TECHNICAL_XMLIDS:
                grp = self.env.ref(xmlid, raise_if_not_found=False)
                if grp:
                    hidden_ids.append(grp.id)

            if hidden_ids:
                visible = Groups.search([('id', 'not in', hidden_ids)])
            else:
                visible = Groups.search([])

        for role in self:
            role.visible_group_ids = visible

    @api.depends('user_ids', 'group_ids')
    def _compute_counts(self):
        for role in self:
            role.user_count = len(role.user_ids)
            role.group_count = len(role.group_ids)

    @api.onchange('source_user_id')
    def _onchange_source_user_id(self):
        """Just a visual hint — actual copy happens on button click."""
        pass

    def action_apply_source_user(self):
        """Button: copy groups from source_user_id into this role."""
        self.ensure_one()
        if not self.source_user_id:
            return
        self.env.cr.execute(
            "SELECT gid FROM res_groups_users_rel WHERE uid = %s",
            (self.source_user_id.id,)
        )
        rows = self.env.cr.fetchall()
        if rows:
            group_ids = [r[0] for r in rows]
            self.write({'group_ids': [(6, 0, group_ids)]})


    def write(self, vals):
        old_groups_per_role = {}
        if 'group_ids' in vals:
            old_groups_per_role = {r.id: r.group_ids for r in self}

        res = super().write(vals)

        if 'group_ids' in vals:
            for role in self:
                old_groups = old_groups_per_role.get(role.id) or self.env['res.groups']
                added = role.group_ids - old_groups
                removed = old_groups - role.group_ids
                if not added and not removed:
                    continue
                for user in role.user_ids:
                    if added:
                        for group in added:
                            self.env.cr.execute(
                                """
                                INSERT INTO res_groups_users_rel (gid, uid)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                                """,
                                (group.id, user.id)
                            )
                    if removed:
                        other_role_groups = (user.role_ids - role).mapped('group_ids')
                        to_remove = removed - other_role_groups
                        if to_remove:
                            self.env.cr.execute(
                                """
                                DELETE FROM res_groups_users_rel
                                WHERE uid = %s AND gid = ANY(%s)
                                """,
                                (user.id, to_remove.ids)
                            )


                    self.env.cr.execute(
                        "SELECT gid FROM res_groups_users_rel WHERE uid = %s",
                        (user.id,)
                    )
                    current_gids = {r[0] for r in self.env.cr.fetchall()}

                    all_role_group_ids = set(user.role_ids.mapped('group_ids').ids)

                    extra_gids = list(current_gids - all_role_group_ids)
                    if extra_gids:
                        self.env.cr.execute(
                            """
                            DELETE FROM res_groups_users_rel
                            WHERE uid = %s AND gid = ANY(%s)
                            """,
                            (user.id, extra_gids)
                        )


                    user.invalidate_recordset()

        if 'notify_by_odoo' in vals and 'notification_type' in self.env['res.users']._fields:
            notification_type = 'inbox' if vals['notify_by_odoo'] else 'email'
            for role in self:
                if role.user_ids:
                    role.user_ids.write({
                        'notification_type': notification_type,
                    })

        return res



    def unlink(self):
        """When a role is deleted, remove its groups from every user who
        had it (preserving groups still granted via other roles)."""
        for role in self:
            for user in role.user_ids:
                other_role_groups = (user.role_ids - role).mapped('group_ids')
                to_remove = role.group_ids - other_role_groups
                if to_remove:
                    self.env.cr.execute(
                        """
                        DELETE FROM res_groups_users_rel
                        WHERE uid = %s AND gid = ANY(%s)
                        """,
                        (user.id, to_remove.ids)
                    )
                    user.invalidate_recordset()
        return super().unlink()


    def action_view_users(self):
        """Open the list of users who have this role."""
        self.ensure_one()
        return {
            'name': 'Users with role: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'list,form',
            'domain': [('role_ids', 'in', self.id)],
            'context': {'default_role_ids': [(4, self.id)]},
        }


    def action_create_user(self):
        """Open new user form with this role pre-assigned."""
        self.ensure_one()
        return {
            'name': 'Create User from Role: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_role_ids': [(4, self.id)],
            },
        }


class SecurityRoleTemporaryRule(models.Model):
    _name = 'security.role.temporary.rule'
    _description = 'Temporary Activation/Blocking Rule'

    role_id = fields.Many2one(
        comodel_name='security.role',
        string='Role',
        required=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=True,
        ondelete='cascade',
    )
    rule_type = fields.Selection(
        selection=[('block', 'Block'), ('activate', 'Activate')],
        string='Type',
        required=True,
        default='block',
    )
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)

    is_applied = fields.Boolean(
        string='Currently Applied',
        default=False,
        help='This field is managed by the scheduler. True indicates that the rule'
             ' is currently within its active period and has already been applied in the database.'
    )

    def is_active_now(self):
        """Check if this rule applies today."""
        today = fields.Date.today()
        return self.date_from <= today <= self.date_to