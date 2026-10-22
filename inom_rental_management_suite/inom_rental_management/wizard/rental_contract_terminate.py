from odoo import fields, models


class PropertyRentalContractTerminate(models.TransientModel):
    _name = 'property.rental.contract.terminate'
    _description = 'Terminate Rental Contract'

    contract_id = fields.Many2one('property.rental.contract', required=True, readonly=True)
    date_terminated = fields.Date(string='Termination Date', required=True, default=fields.Date.context_today)
    termination_reason = fields.Selection(
        selection=lambda self: self.env['property.rental.contract']._fields['termination_reason']._description_selection(self.env),
        string='Reason', required=True,
    )
    termination_note = fields.Text(string='Details')

    def action_terminate(self):
        self.ensure_one()
        self.contract_id._terminate(self.date_terminated, self.termination_reason, self.termination_note)
        return {'type': 'ir.actions.act_window_close'}
