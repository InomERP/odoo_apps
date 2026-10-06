# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        """Register pos.access.rights to be sent to the POS frontend."""
        data = super()._load_pos_data_models(config_id)
        if 'pos.access.rights' not in data:
            data.append('pos.access.rights')
        return data
