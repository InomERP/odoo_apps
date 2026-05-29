# -*- coding: utf-8 -*-
from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_domain(self, data, *args, **kwargs):
        """Restrict partners loaded into POS based on salesperson restriction."""
        domain = super()._load_pos_data_domain(data, *args, **kwargs)
        access = self.env['pos.access.rights'].sudo().search(
            [('user_id', '=', self.env.uid), ('active', '=', True)], limit=1
        )
        if access and access.restrict_salesperson_customers:
            domain = list(domain) + [('user_id', '=', self.env.uid)]
        return domain
