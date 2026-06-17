# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    inom_so_force_cancel_allowed = fields.Boolean(
        string="Allow Sale Order Cancellation",
        help="When enabled, this user is allowed to force cancel confirmed "
             "sale orders, including their already validated deliveries and "
             "posted invoices.",
    )
    inom_mo_force_cancel_allowed = fields.Boolean(
        string="Allow Manufacturing Order Cancellation",
        help="When enabled, this user is allowed to force cancel completed "
             "manufacturing orders, including their finished work orders and "
             "validated stock moves.",
    )