from odoo import fields, models, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = "res.users"

    is_readonly = fields.Boolean(string="Is Readonly", default=False)

    def write(self, vals):
        try:
            readonly_group = self.env.ref('inom_readonly_user.group_users_readonly')
        except Exception:
            return super().write(vals)

        group_key = str(readonly_group.id)

        if group_key in str(vals):
            if self.id == self.env.user.id:
                raise ValidationError(
                    _("Aap apne aap ko readonly nahi bana sakte.")
                )

        return super().write(vals)