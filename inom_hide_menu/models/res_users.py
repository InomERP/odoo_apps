from odoo import fields, models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    hide_menu_ids = fields.Many2many('ir.ui.menu', string="Hide Menus",
        help="Menus that will be hidden for this user."
    )

    def write(self, vals):
        previous_menu_map = {rec.id: rec.hide_menu_ids for rec in self}
        result = super().write(vals)

        for rec in self:
            previous_menus = previous_menu_map.get(rec.id, self.env['ir.ui.menu'])
            # Only apply restriction for newly added menus
            added_menus = rec.hide_menu_ids - previous_menus
            for menu in added_menus:
                menu.sudo().write({'restricted_user_ids': [(4, rec.id)]})
            # Remove restriction from menus that were unselected
            removed_menus = previous_menus - rec.hide_menu_ids
            for menu in removed_menus:
                menu.sudo().write({'restricted_user_ids': [(3, rec.id)]})
        return result

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    restricted_user_ids = fields.Many2many('res.users', string="Restricted Users",
        help="Users who cannot see this menu."
    )

    def _filter_visible_menus(self):
        menus = super()._filter_visible_menus()
        # Admin sees all menus
        if self.env.user.has_group('base.group_system'):
            return menus
        # Only hide menus that are explicitly restricted for the user
        return menus.filtered(lambda m: self.env.user not in m.restricted_user_ids.sudo())