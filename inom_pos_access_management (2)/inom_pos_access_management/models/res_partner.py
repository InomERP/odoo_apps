# -*- coding: utf-8 -*-
from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _inom_customer_restriction_domain(self):
        """Return the extra domain for a salesperson restricted to their own customers."""
        access = self.env['pos.access.rights'].sudo().search(
            [('user_id', '=', self.env.uid), ('active', '=', True)], limit=1
        )
        if not (access and access.restrict_salesperson_customers):
            return []
        return [
            '|',
            ('user_id', '=', self.env.uid),
            ('id', '=', self.env.user.partner_id.id),
        ]

    @api.model
    def _load_pos_data_domain(self, data, *args, **kwargs):
        """Restrict partners loaded into POS based on salesperson restriction."""
        domain = super()._load_pos_data_domain(data, *args, **kwargs)
        extra = self._inom_customer_restriction_domain()
        return list(domain) + extra if extra else domain

    @api.model
    def _load_pos_metadata(self, data, search_params={}):
        """The POS partner search sends its own domain, which replaces
        ``_load_pos_data_domain``; keep the salesperson restriction on it."""
        extra = self._inom_customer_restriction_domain()
        if extra and search_params.get('domain'):
            search_params = {**search_params, 'domain': list(search_params['domain']) + extra}
        return super()._load_pos_metadata(data, search_params)
