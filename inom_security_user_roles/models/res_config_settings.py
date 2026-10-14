# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_technical_user_groups_without_dev_mode = fields.Boolean(
        string='Show technical user groups on roles forms without developer mode',
        config_parameter='inom_security_user_roles.show_technical_user_groups_without_dev_mode',
        default=False,
    )
