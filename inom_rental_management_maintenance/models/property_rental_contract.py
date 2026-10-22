from odoo import fields, models


class PropertyRentalContract(models.Model):
    _inherit = 'property.rental.contract'

    maintenance_request_ids = fields.One2many('maintenance.request', 'rental_contract_id', string='Maintenance Requests')
    maintenance_request_count = fields.Integer(compute='_compute_maintenance_request_count')

    def _compute_maintenance_request_count(self):
        counts = dict(self.env['maintenance.request']._read_group(
            [('rental_contract_id', 'in', self.ids)], groupby=['rental_contract_id'], aggregates=['__count'],
        ))
        for contract in self:
            contract.maintenance_request_count = counts.get(contract, 0)

    def action_view_maintenance_requests(self):
        self.ensure_one()
        action = self.property_id.action_view_maintenance_requests()
        action['domain'] = [('rental_contract_id', '=', self.id)]
        action['context'] = dict(action['context'], default_rental_contract_id=self.id)
        return action

    def action_new_maintenance_request(self):
        self.ensure_one()
        action = self.property_id.action_new_maintenance_request()
        action['context'] = dict(action['context'], default_rental_contract_id=self.id)
        return action
