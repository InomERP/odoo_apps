from odoo import api, models
from odoo.exceptions import AccessError

class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    SYSTEM_MODELS = {
        'res.users.log',
        'res.users',
        'bus.presence',
        'bus.bus',
        'mail.channel',
        'mail.channel.member',
        'mail.alias',
        'mail.message',
        'mail.message.subtype',
        'mail.notification',
        'mail.followers',
        'mail.tracking.value',
        'ir.config_parameter',
        'ir.attachment',
        'ir.ui.view',
        'ir.rule',
        'ir.model.access',
        'ir.model',
        'ir.module.module',
        'res.lang',
        'res.groups',
        'res.partner',
        'ir.model.data',
        'ir.sequence',
        'base.setup.installer',
    }

    @api.model
    def check(self, model_name, mode='read', raise_exception=False):
        try:

            is_readonly = self.env.user.has_group(
                'inom_readonly_user.group_users_readonly'
            )
        except Exception:
            return super().check(model_name, mode=mode, raise_exception=raise_exception)

        if is_readonly:
            if model_name in self.SYSTEM_MODELS:
                return super().check(model_name, mode=mode, raise_exception=raise_exception)

            if self.env.su:
                return super().check(model_name, mode=mode, raise_exception=raise_exception)

            if mode in ('write', 'create', 'unlink'):
                if raise_exception:
                    raise AccessError(
                        "You have readonly access. You cannot modify records."
                    )
                return False

        return super().check(model_name, mode=mode, raise_exception=raise_exception)