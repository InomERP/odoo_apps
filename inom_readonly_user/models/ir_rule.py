from odoo import api, models
from odoo.fields import Domain


class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _compute_domain(self,model_name,mode):
        res = super(IrRule, self)._compute_domain(model_name,mode)
        readonly_models = ['res.users.log','res.users','mail.channel','mail.alias','bus.presence',
                           'res.lang','mail.channel.member']

        if self.env.user.has_group('inom_readonly_user.group_users_readonly')\
            and model_name in readonly_models\
            and mode  in ('write','create','unlink'):
            return Domain.AND([res,Domain.FALSE])
        return res
