# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inom_version_display_mode = fields.Selection(
        selection=[
            ('all', 'Show All Versions'),
            ('latest', 'Show Latest Version Only'),
        ],
        string="Order Versions Display",
        default='all',
        config_parameter='inom_sale_order_versioning.display_mode',
        help="Choose whether the order list shows every version or only the "
             "latest version of each chain.",
    )
    inom_auto_cancel_previous = fields.Boolean(
        string="Auto-cancel Previous Version",
        config_parameter='inom_sale_order_versioning.auto_cancel_previous',
        help="When a new version is confirmed, automatically cancel the earlier "
             "confirmed versions in the same chain. Versions that already have a "
             "posted invoice are kept and only flagged.",
    )
