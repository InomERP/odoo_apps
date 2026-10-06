# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_contract_for_invoice = fields.Boolean(
        string='Use Contracts on Invoices',
        config_parameter='inom_contract_management.use_contract_for_invoice',
        help='Enable using contracts as a source/template for '
             'customer invoices and vendor bills.',
    )
    use_contract_approval = fields.Boolean(
        string='Use Contract Approval Workflow',
        config_parameter='inom_contract_management.use_contract_approval',
        help='Enable the multi-step approval workflow for contracts. '
             'If disabled, contracts move directly from Draft to Running '
             'when confirmed.',
    )
