# -*- coding: utf-8 -*-
from odoo import models, api


class PosOrder(models.Model):
    """Pre-filter pos.order records returned to the POS Ticket Screen.

    Odoo 17 vs Odoo 18
    ------------------
    In Odoo 18 the POS UI obtains paid orders through the
    ``pos.load.mixin`` machinery, and the original module customised
    ``_load_pos_data_domain``.  Odoo 17 does NOT pre-load paid orders at
    session start — instead the Ticket Screen calls
    ``pos.order.search_paid_order_ids`` (a JSON-RPC) on demand whenever
    the cashier opens the orders tab or types in the search bar.

    Overriding that method here is the exact 17-equivalent of the
    Odoo-18 hook: it lets us shrink the result set at the data layer so
    other-staff orders never reach the cashier in the first place,
    regardless of any UI filtering done in JS.
    """
    _inherit = 'pos.order'

    @api.model
    def search_paid_order_ids(self, config_id, domain, limit, offset):
        """Authoritative server-side restriction for the salesperson rule.

        POS Managers and System Administrators always see everything;
        every other user matching an active ``pos.access.rights`` record
        with ``restrict_salesperson_orders=True`` sees only orders they
        created themselves OR orders linked to their ``hr.employee``.
        """
        user = self.env.user
        # POS Managers and System Administrators always see everything.
        if not (
            user.has_group('point_of_sale.group_pos_manager')
            or user.has_group('base.group_system')
        ):
            access = self.env['pos.access.rights'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True),
                ('restrict_salesperson_orders', '=', True),
            ], limit=1)
            if access:
                employee = self.env['hr.employee'].sudo().search(
                    [('user_id', '=', user.id)], limit=1,
                )
                if employee:
                    extra = [
                        '|',
                        ('employee_id', '=', employee.id),
                        ('user_id', '=', user.id),
                    ]
                else:
                    extra = [('user_id', '=', user.id)]
                domain = list(domain or []) + extra
        return super().search_paid_order_ids(config_id, domain, limit, offset)
