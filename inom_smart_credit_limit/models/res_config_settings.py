# -*- coding: utf-8 -*-
# Part of INOM Smart Credit Limit. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

CHECKPOINT_SELECTION = [
    ('off', 'Do Nothing'),
    ('warn', 'Warn Only'),
    ('block', 'Block'),
]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inom_checkpoint_so = fields.Selection(
        selection=CHECKPOINT_SELECTION,
        string="Sale Order Confirmation",
        default='block',
        config_parameter='inom_smart_credit_limit.checkpoint_so',
        help="Action taken when confirming a sale order that exceeds "
             "the customer's smart credit limit.")
    inom_checkpoint_delivery = fields.Selection(
        selection=CHECKPOINT_SELECTION,
        string="Delivery Validation",
        default='warn',
        config_parameter='inom_smart_credit_limit.checkpoint_delivery',
        help="Action taken when validating an outgoing delivery for a "
             "customer who is over the limit or on hold.")
    inom_checkpoint_invoice = fields.Selection(
        selection=CHECKPOINT_SELECTION,
        string="Invoice Posting",
        default='off',
        config_parameter='inom_smart_credit_limit.checkpoint_invoice',
        help="Action taken when posting a direct customer invoice "
             "(invoices linked to sale orders are already covered).")
    inom_auto_hold_days = fields.Integer(
        string="Auto Hold After (Days Overdue)",
        default=60,
        config_parameter='inom_smart_credit_limit.auto_hold_days',
        help="Place the customer on automatic credit hold when any "
             "invoice is overdue for more than this number of days. "
             "Set 0 to disable automatic holds.")
    inom_auto_release = fields.Boolean(
        string="Automatic Release",
        default=True,
        config_parameter='inom_smart_credit_limit.auto_release',
        help="Automatically release automatic holds once no invoice "
             "remains beyond the aging threshold.")
    inom_scoring_active = fields.Boolean(
        string="Smart Scoring Reviews",
        default=True,
        config_parameter='inom_smart_credit_limit.scoring_active',
        help="Enable the monthly smart scoring review that suggests "
             "limit adjustments to credit managers.")
