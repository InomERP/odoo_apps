from odoo.tests import HttpCase, tagged

WAIT_FOR = """
    const selector = %r;
    const started = Date.now();
    const timer = setInterval(() => {
        if (document.querySelector(selector)) {
            clearInterval(timer);
            console.log('test successful');
        } else if (Date.now() - started > 20000) {
            clearInterval(timer);
            console.error('Timed out waiting for ' + selector);
        }
    }, 100);
"""


@tagged('post_install', '-at_install')
class TestMaintenanceUi(HttpCase):

    def test_property_and_request_forms_render(self):
        ptype = self.env['property.type'].create({'name': 'UI type P10', 'category': 'residential'})
        owner = self.env['res.partner'].create({'name': 'UI owner P10', 'is_property_owner': True})
        prop = self.env['property.property'].create({'name': 'UI flat P10', 'type_id': ptype.id, 'owner_id': owner.id})
        team = self.env['maintenance.team'].search([], limit=1) or self.env['maintenance.team'].create({'name': 'UI team'})
        request = self.env['maintenance.request'].create({
            'name': 'UI request', 'property_id': prop.id, 'maintenance_team_id': team.id,
        })
        self.browser_js(f'/odoo/action-inom_rental_management.action_property_property/{prop.id}',
                        WAIT_FOR % 'button[name="action_view_maintenance_requests"]', login='admin')
        self.browser_js(f'/odoo/action-inom_rental_management_maintenance.action_property_maintenance_requests/{request.id}',
                        WAIT_FOR % '.o_field_widget[name="property_id"]', login='admin')
