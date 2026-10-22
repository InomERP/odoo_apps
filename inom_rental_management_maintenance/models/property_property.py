from odoo import api, fields, models
from odoo.exceptions import UserError


class PropertyProperty(models.Model):
    _name = 'property.property'
    _inherit = ['property.property', 'maintenance.mixin']

    maintenance_ids = fields.One2many('maintenance.request', 'property_id', string='Maintenance Requests')

    @api.ondelete(at_uninstall=False)
    def _unlink_keep_maintenance_history(self):
        if self.env['maintenance.request'].sudo().search_count([('property_id', 'in', self.ids)], limit=1):
            raise UserError(self.env._(
                "This property has maintenance history: archive it instead of deleting it."
            ))

    def _maintenance_request_defaults(self):
        self.ensure_one()
        defaults = {'default_property_id': self.id, 'default_company_id': self.company_id.id}
        if self.maintenance_team_id:
            defaults['default_maintenance_team_id'] = self.maintenance_team_id.id
        if self.technician_user_id:
            defaults['default_user_id'] = self.technician_user_id.id
        return defaults

    def action_view_maintenance_requests(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('maintenance.hr_equipment_request_action')
        action['domain'] = [('property_id', '=', self.id)]
        action['context'] = dict(self._maintenance_request_defaults(), search_default_filter_not_archived=0)
        return action

    def action_new_maintenance_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("New Maintenance Request"),
            'res_model': 'maintenance.request',
            'view_mode': 'form',
            'context': self._maintenance_request_defaults(),
        }
