# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResCompany(models.Model):
    """Add inter company stock transfer configuration on the company."""
    _inherit = 'res.company'

    intercompany_transfer_enabled = fields.Boolean(
        string="Inter Company Transfer",
        help="When enabled, an opposite stock operation is automatically "
             "created in this company whenever another company validates a "
             "transfer addressed to this company.",
    )
    intercompany_transfer_apply_on = fields.Selection(
        selection=[
            ('both', "Delivery and Receipts"),
            ('receipt', "Receipt"),
            ('delivery', "Delivery Order"),
        ],
        string="Apply On",
        default='both',
        help="Source operation type, in the other company, that triggers an "
             "automatic counterpart operation in this company.",
    )
    intercompany_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string="Warehouse",
        help="Warehouse of this company used to create the automatic "
             "counterpart operation.",
    )
    intercompany_transfer_note = fields.Char(
        string="Inter Company Transfer Note",
        compute='_compute_intercompany_transfer_note',
        help="Informative summary of the configured inter company behaviour.",
    )

    @api.depends('name', 'intercompany_warehouse_id')
    def _compute_intercompany_transfer_note(self):
        """Build the informative sentence shown on the configuration tab."""
        for company in self:
            warehouse_name = company.intercompany_warehouse_id.name or ''
            company.intercompany_transfer_note = _(
                "Create a Delivery Order / Receipt Order when a company "
                "validates a Receipt / Delivery Order for %(company)s using "
                "%(warehouse)s Warehouse.",
            ) % {
                'company': company.name or '',
                'warehouse': warehouse_name,
            }
