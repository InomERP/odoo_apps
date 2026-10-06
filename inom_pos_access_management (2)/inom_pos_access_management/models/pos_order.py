# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.fields import Domain


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _inom_salesperson_restriction_enabled(self):
        """Return whether the current POS user is restricted to their own orders."""
        user = self.env.user
        if (
            user.has_group('point_of_sale.group_pos_manager')
            or user.has_group('base.group_system')
        ):
            return False
        return bool(self.env['pos.access.rights'].sudo().search([
            ('user_id', '=', user.id),
            ('active', '=', True),
            ('restrict_salesperson_orders', '=', True),
        ], limit=1))

    def _inom_salesperson_domain(self):
        """Return the server-side domain for the current salesperson."""
        if not self._inom_salesperson_restriction_enabled():
            return []
        user_id = self.env.uid
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', user_id)], limit=1,
        )
        # pos.order.employee_id only exists when pos_hr is installed.
        if employee and 'employee_id' in self._fields:
            return [
                '|',
                ('employee_id', '=', employee.id),
                ('user_id', '=', user_id),
            ]
        return [('user_id', '=', user_id)]

    @api.model
    def _load_pos_data_domain(self, data, *args, **kwargs):
        """Pre-filter draft orders loaded into the POS frontend."""
        domain = super()._load_pos_data_domain(data, *args, **kwargs)
        extra = self._inom_salesperson_domain()
        return list(domain) + extra if extra else domain

    @api.model
    def search_order_ids(self, config_id, domain, limit, offset, state_filter='paid'):
        """Also apply salesperson restriction to Ticket Screen server searches.

        Odoo 20 Ticket Screen uses ``search_order_ids`` for paginated paid/cancelled
        orders, so restricting only ``_load_pos_data_domain`` is not sufficient.
        """
        extra = self._inom_salesperson_domain()
        if extra:
            domain = Domain(domain or []) & Domain(extra)
        return super().search_order_ids(
            config_id, domain, limit, offset, state_filter
        )

    @api.model
    def read_pos_orders(self, domain=False):
        """Protect direct POS order reads as well as normal Ticket Screen loading."""
        extra = self._inom_salesperson_domain()
        if extra:
            domain = Domain(domain or []) & Domain(extra)
        return super().read_pos_orders(domain)

