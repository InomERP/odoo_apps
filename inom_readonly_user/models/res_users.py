from odoo import _, fields, models
from odoo.exceptions import ValidationError

READONLY_GROUP = "inom_readonly_user.group_users_readonly"


class ResUsers(models.Model):
    _inherit = "res.users"

    is_readonly = fields.Boolean(string="Is Readonly", default=False)

    def write(self, vals):
        current_user = self.env.user
        was_readonly = current_user in self and current_user._has_group(READONLY_GROUP)
        res = super().write(vals)
        # Prevent the current user from locking themselves into readonly mode.
        if (
            current_user in self
            and not was_readonly
            and current_user._has_group(READONLY_GROUP)
        ):
            raise ValidationError(_("Readonly access denied for Admin"))
        return res
