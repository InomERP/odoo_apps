# -*- coding: utf-8 -*-
from odoo import fields, models


class InomContractReturnWizard(models.TransientModel):
    _name = 'inom.contract.return.wizard'
    _description = 'Return Contract for Correction'

    contract_id = fields.Many2one(
        comodel_name='inom.contract',
        string='Contract',
        required=True,
        ondelete='cascade',
    )
    comment = fields.Text(
        string='Reason / Comment',
        required=True,
        help='Explain what needs to be corrected. This will be sent to the '
             'responsible person.',
    )

    def action_return(self):
        self.ensure_one()
        self.contract_id._apply_return(self.comment)
        return {'type': 'ir.actions.act_window_close'}