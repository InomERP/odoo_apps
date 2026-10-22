from odoo import api, models

# Demo properties looked after by the demo maintenance team, with their technician if any.
DEMO_TEAM_PROPERTIES = {
    'inom_rental_management.demo_property_skyline_a101': 'base.user_admin',
    'inom_rental_management.demo_property_skyline_b201': False,
    'inom_rental_management.demo_property_green_villa': False,
}


class PropertyRentalDemo(models.AbstractModel):
    _inherit = 'property.rental.demo'

    @api.model
    def _load_maintenance_demo(self):
        """ Assign the demo maintenance team to demo properties that have none. Done in code because
        an upgrade skips overrides of the core module's demo records (they are noupdate). """
        team = self.env.ref('inom_rental_management_maintenance.demo_team_property_care', raise_if_not_found=False)
        if not team:
            return
        for xmlid, technician in DEMO_TEAM_PROPERTIES.items():
            prop = self.env.ref(xmlid, raise_if_not_found=False)
            if prop and not prop.maintenance_team_id and team.company_id in (prop.company_id, self.env['res.company']):
                vals = {'maintenance_team_id': team.id}
                if technician and not prop.technician_user_id:
                    vals['technician_user_id'] = self.env.ref(technician).id
                prop.write(vals)
