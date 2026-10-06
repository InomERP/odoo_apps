from odoo import api, fields, models
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    # Both sides of the relation share the same table, so Odoo treats
    # ir.ui.menu.restricted_user_ids as the inverse of this field and no
    # manual synchronization is needed.
    hide_menu_ids = fields.Many2many(
        "ir.ui.menu",
        "ir_ui_menu_res_users_rel",
        "res_users_id",
        "ir_ui_menu_id",
        string="Hide Menus",
        help="Menus that will be hidden for this user.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if any(vals.get("hide_menu_ids") for vals in vals_list):
            self.env.transaction.invalidate_ormcache()
        return users

    def _get_invalidation_fields(self):
        # load_menus() / load_menus_root() are ormcached per uid, so the
        # cache must be cleared when the hidden menus of a user change.
        return super()._get_invalidation_fields() | {"hide_menu_ids"}


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    restricted_user_ids = fields.Many2many(
        "res.users",
        "ir_ui_menu_res_users_rel",
        "ir_ui_menu_id",
        "res_users_id",
        string="Restricted Users",
        help="Users who cannot see this menu.",
    )

    @api.model
    def _get_user_hidden_menu_ids(self):
        """Return the ids of the menus hidden for the current user: the
        configured menus, all their sub-menus, and the parent folders left
        without any visible action menu."""
        user = self.env.user
        # Only the superuser (OdooBot) bypasses the restriction.
        if user._is_superuser():
            return frozenset()
        hidden_menus = user.sudo().hide_menu_ids
        if not hidden_menus:
            return frozenset()

        Menu = self.sudo().with_context(active_test=False)
        blocked_ids = set(Menu.search([("id", "child_of", hidden_menus.ids)]).ids)

        debug = request.session.debug if request else False
        visible = Menu.browse(self._visible_menu_ids(debug)).filtered(
            lambda menu: menu.id not in blocked_ids
        )
        visible_ids = set(visible.ids)

        # Keep only menus with an action and their ancestors, so that a
        # parent menu whose children are all hidden disappears as well.
        kept_ids = set()
        for menu in visible.filtered("action"):
            while menu and menu.id in visible_ids and menu.id not in kept_ids:
                kept_ids.add(menu.id)
                menu = menu.parent_id

        return frozenset(blocked_ids | (visible_ids - kept_ids))

    def _filter_visible_menus(self):
        menus = super()._filter_visible_menus()
        hidden_ids = self._get_user_hidden_menu_ids()
        if not hidden_ids:
            return menus
        return menus.filtered(lambda menu: menu.id not in hidden_ids)
