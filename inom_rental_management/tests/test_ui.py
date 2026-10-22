from odoo.tests import HttpCase, new_test_user, tagged

# Waits until the given selector is rendered, then reports success; any JS error fails the test.
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
class TestPropertyUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        new_test_user(cls.env, 'ui_agent', groups='inom_rental_management.group_rental_agent')
        property_type = cls.env['property.type'].create({'name': 'UI Apartment', 'category': 'residential'})
        owner = cls.env['res.partner'].create({'name': 'UI Owner', 'is_property_owner': True})
        cls.property = cls.env['property.property'].create({
            'name': 'UI Skyline A-101', 'type_id': property_type.id, 'owner_id': owner.id,
            'bedrooms': 2, 'bathrooms': 1, 'total_area': 950.0, 'rent_price': 18000.0,
        })
        cls.owner = owner
        cls.tenant = cls.env['res.partner'].create({'name': 'UI Tenant', 'is_tenant': True})
        cls.env['property.partner.document'].create({
            'name': 'UI Passport', 'partner_id': cls.tenant.id, 'document_type': 'identity',
        })
        sale_property = cls.env['property.property'].create({
            'name': 'UI Villa', 'type_id': property_type.id, 'owner_id': owner.id,
            'property_for': 'sale', 'sale_price': 900000.0,
        })
        buyer = cls.env['res.partner'].create({'name': 'UI Buyer', 'is_property_buyer': True})
        cls.sale = cls.env['property.sale.contract'].create({
            'property_id': sale_property.id, 'buyer_id': buyer.id, 'booking_amount': 90000.0,
        })
        cls.sale.action_book()
        cls.lease = cls.env['property.rental.contract'].create({
            'property_id': cls.property.id, 'tenant_id': cls.tenant.id,
            'date_start': '2026-01-01', 'date_end': '2026-12-31',
        })
        cls.lease.action_start()
        cls.env['crm.lead'].create({
            'name': 'UI enquiry', 'type': 'opportunity', 'partner_id': buyer.id,
            'property_for': 'sale', 'property_id': sale_property.id,
        })

    def _open(self, path, selector, login):
        self.browser_js(path, WAIT_FOR % selector, login=login)

    def _check_property_views(self, login):
        base = '/odoo/action-inom_rental_management.action_property_property'
        self._open(f'{base}?view_type=kanban', '.o_kanban_record:not(.o_kanban_ghost)', login)
        self._open(f'{base}?view_type=list', '.o_data_row', login)
        self._open(f'{base}/{self.property.id}', '.o_form_view .o_field_widget[name="bedrooms"]', login)

    def test_property_views_render_admin(self):
        self._check_property_views('admin')

    def test_property_views_render_agent(self):
        self._check_property_views('ui_agent')

    def test_owner_smart_button_renders(self):
        self._open(f'/odoo/action-base.action_partner_form/{self.owner.id}', 'button[name="action_view_owned_properties"]', 'admin')

    def test_tenant_contact_and_documents_render(self):
        self._open(f'/odoo/action-base.action_partner_form/{self.tenant.id}',
                   'button[name="action_view_real_estate_documents"]', 'admin')
        self._open('/odoo/action-inom_rental_management.action_property_partner_document', '.o_data_row', 'admin')

    def test_sale_and_enquiry_views_render(self):
        self._open(f'/odoo/action-inom_rental_management.action_property_sale_contract/{self.sale.id}',
                   'button[name="action_create_booking_invoice"]', 'admin')
        self._open('/odoo/action-inom_rental_management.action_property_enquiry', '.o_kanban_record:not(.o_kanban_ghost)', 'admin')

    def test_rental_contract_views_render(self):
        base = '/odoo/action-inom_rental_management.action_property_rental_contract'
        self._open(f'{base}/{self.lease.id}', 'button[name="action_open_renew_wizard"]', 'admin')
        self._open(f'{base}?view_type=calendar', '.o_calendar_renderer', 'admin')

    def test_rent_views_render(self):
        base = '/odoo/action-inom_rental_management.action_property_rental_contract'
        self._open(f'{base}/{self.lease.id}', 'div[name="rent_schedule_ids"] .o_data_row', 'admin')
        self._open('/odoo/action-inom_rental_management.action_rent_schedule', '.o_data_row', 'admin')
        self._open('/odoo/action-inom_rental_management.action_deposit_status', '.o_list_view', 'admin')

    def test_enquiry_views_render(self):
        lead = self.env['crm.lead'].search([('name', '=', 'UI enquiry')], limit=1)
        self._open(f'/odoo/action-inom_rental_management.action_property_enquiry_all/{lead.id}',
                   'button[name="action_create_property_sale"]', 'admin')
        self._open('/odoo/action-inom_rental_management.action_property_enquiry_analysis', '.o_pivot', 'admin')

    def test_dashboard_renders(self):
        self._open('/odoo/action-inom_rental_management.action_rental_dashboard', '.o_rental_tile_total .o_rental_tile_value', 'admin')
