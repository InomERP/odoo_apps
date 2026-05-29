# -*- coding: utf-8 -*-
from odoo import models, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _load_pos_data_domain(self, data, *args, **kwargs):
        """Pre-filter pos.order records loaded into the POS front-end.

        Authoritative server-side restriction is enforced by the ir.rule
        `rule_pos_order_salesperson_visibility` (security/pos_order_visibility.xml),
        which applies on every read — including direct URL access from the
        backend. This override simply narrows the initial dataset sent to
        the POS UI so the cashier never receives other people's orders in
        the first place.
        """
        domain = super()._load_pos_data_domain(data, *args, **kwargs)
        user = self.env.user
        # POS Managers and System Administrators always see everything.
        if (
            user.has_group('point_of_sale.group_pos_manager')
            or user.has_group('base.group_system')
        ):
            return domain
        access = self.env['pos.access.rights'].sudo().search([
            ('user_id', '=', user.id),
            ('active', '=', True),
            ('restrict_salesperson_orders', '=', True),
        ], limit=1)
        if not access:
            return domain
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
        return list(domain) + extra




# # -*- coding: utf-8 -*-
# from odoo import models, api


# class PosOrder(models.Model):
#     _inherit = 'pos.order'

#     @api.model
#     def _load_pos_data_domain(self, data, *args, **kwargs):
#         domain = super()._load_pos_data_domain(data, *args, **kwargs)
#         access = self.env['pos.access.rights'].sudo().search(
#             [('user_id', '=', self.env.uid), ('active', '=', True)], limit=1
#         )
#         if access and access.restrict_salesperson_orders:
#             employee = self.env['hr.employee'].sudo().search(
#                 [('user_id', '=', self.env.uid)], limit=1
#             )
#             if employee:
#                 domain = list(domain) + [('employee_id', '=', employee.id)]
#             else:
#                 domain = list(domain) + [('user_id', '=', self.env.uid)]
#         return domain









