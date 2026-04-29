from odoo import api, models
from odoo.osv import expression

class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _compute_domain(self, model_name, mode):
        res = super(IrRule, self)._compute_domain(model_name, mode)


        readonly_models = [
            'mail.channel',
            'mail.alias',
            'mail.channel.member',
            'res.lang',
        ]

        res_users_blocked_modes = ('create', 'unlink')

        if self.env.user.has_group('inom_readonly_user.group_users_readonly'):

            if model_name == 'res.users' and mode in res_users_blocked_modes:
                false_domain = [(0, '=', 1)]
                return expression.AND([res or [], false_domain])

            if model_name in readonly_models and mode in ('write', 'create', 'unlink'):
                false_domain = [(0, '=', 1)]
                return expression.AND([res or [], false_domain])

        return res