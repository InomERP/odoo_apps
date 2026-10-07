# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class InomMassTransferWizard(models.TransientModel):
    _name = 'inom.mass.transfer.wizard'
    _description = 'Mass Asset Transfer Wizard'

    asset_ids = fields.Many2many(
        'inom.asset', string='Assets', required=True,
        domain="[('state', '!=', 'scrapped')]")
    transfer_type = fields.Selection([
        ('location', 'Location Change'),
        ('custody', 'Custody Change'),
        ('both', 'Location + Custody'),
    ], string='Transfer Type', default='location', required=True)
    destination_location_id = fields.Many2one(
        'inom.asset.location', string='To Location')
    destination_employee_id = fields.Many2one(
        'hr.employee', string='To Custodian')
    transfer_date = fields.Datetime(
        string='Transfer Date', default=fields.Datetime.now)
    reason = fields.Text(string='Reason')
    auto_submit = fields.Boolean(
        string='Submit for Approval Immediately', default=True)

    def action_create_transfers(self):
        self.ensure_one()
        if self.transfer_type in ('location', 'both') \
                and not self.destination_location_id:
            raise UserError(_('Destination location is required.'))
        if self.transfer_type in ('custody', 'both') \
                and not self.destination_employee_id:
            raise UserError(_('Destination custodian is required.'))
        transfers = self.env['inom.asset.transfer'].create([{
            'asset_id': asset.id,
            'transfer_type': self.transfer_type,
            'destination_location_id': self.destination_location_id.id,
            'destination_employee_id': self.destination_employee_id.id,
            'transfer_date': self.transfer_date,
            'reason': self.reason,
        } for asset in self.asset_ids])
        if self.auto_submit:
            transfers.action_submit()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Transfers'),
            'res_model': 'inom.asset.transfer',
            'view_mode': 'list,form',
            'domain': [('id', 'in', transfers.ids)],
        }
