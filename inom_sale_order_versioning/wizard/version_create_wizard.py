# -*- coding: utf-8 -*-
from odoo import fields, models, _


class InomVersionCreateWizard(models.TransientModel):
    _name = 'inom.version.create.wizard'
    _description = 'Create Order Version Wizard'

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Source Order",
        required=True,
        readonly=True,
    )
    reason_type = fields.Selection(
        selection=[
            ('price', 'Price Change'),
            ('scope', 'Scope / Lines Change'),
            ('terms', 'Terms Change'),
            ('customer', 'Customer Request'),
            ('other', 'Other'),
        ],
        string="Reason",
        default='other',
        required=True,
    )
    reason = fields.Text(
        string="Note",
        help="Optional explanation that will be stored on the new version.",
    )

    def action_inom_confirm_create(self):
        self.ensure_one()
        new_version = self.order_id._inom_create_version(
            reason_type=self.reason_type,
            reason=self.reason,
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Order Version'),
            'res_model': 'sale.order',
            'res_id': new_version.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
