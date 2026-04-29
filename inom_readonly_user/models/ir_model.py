
from odoo import api, models
from odoo.exceptions import AccessError


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    def check(self, model_name, mode='read', raise_exception=False):

        blocked_models = [
            'res.users.log', 'mail.channel', 'mail.alias',
            'bus.presence', 'res.lang', 'mail.channel.member'
        ]

        if self.env.user.has_group('inom_readonly_user.group_users_readonly'):

            if model_name in blocked_models and mode in ('write', 'create', 'unlink'):
                if raise_exception:
                    raise AccessError(
                        "You have readonly access. You cannot modify records."
                    )
                return False

            if mode in ('write', 'create', 'unlink'):
                if raise_exception:
                    raise AccessError(
                        "You have readonly access. You cannot modify records."
                    )
                return False

        return super().check(model_name, mode=mode, raise_exception=raise_exception)