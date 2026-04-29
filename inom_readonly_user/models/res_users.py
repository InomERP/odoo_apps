from odoo import fields, models, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = "res.users"

    is_readonly = fields.Boolean(string="Is Readonly",default=False)

    def write(self, vals):
        group_obj = self.env['res.groups'].sudo().browse(self.env.ref('inom_readonly_user.group_users_readonly').id)
        if str(group_obj.id) in str(vals):
            if self.id == self.env.user.id:
                raise ValidationError(
                    _("Readonly access denied for Admin"))
            else:
                super(ResUsers, self).write(vals)
        else:
            super(ResUsers, self).write(vals)


