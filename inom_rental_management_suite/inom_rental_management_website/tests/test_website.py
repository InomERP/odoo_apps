import base64
import re

from odoo.exceptions import AccessError
from odoo.tests import HttpCase, new_test_user, tagged

PNG = base64.b64encode(bytes.fromhex(
    '89504e470d0a1a0a0000000d4948445200000001000000010806000000'
    '1f15c4890000000d4944415478da63f8ffff3f0005fe02fea7d65e9f0000000049454e44ae426082'
))


@tagged('post_install', '-at_install')
class TestPropertyWebsite(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(cls.env, 'p9_agent', groups='inom_rental_management.group_rental_agent,sales_team.group_sale_salesman')
        cls.manager = new_test_user(cls.env, 'p9_manager', groups='inom_rental_management.group_rental_manager')
        cls.website = cls.env['website'].get_current_website()
        ptype = cls.env['property.type'].create({'name': 'Penthouse P9', 'category': 'residential'})
        cls.owner = cls.env['res.partner'].create({'name': 'Secret Owner Name', 'is_property_owner': True})
        cls.tenant = cls.env['res.partner'].create({'name': 'Hidden Tenant Name', 'is_tenant': True})

        def make(name, **vals):
            prop = cls.env['property.property'].create({
                'name': name, 'type_id': ptype.id, 'owner_id': cls.owner.id, 'user_id': cls.agent.id,
                'rent_price': 25000.0, 'city': 'Ahmedabad', 'bedrooms': 3,
                'description': '<p>INTERNAL NOTE do not publish</p>',
                'website_description': f'<p>Public text for {name}</p>',
                'image_1920': PNG, **vals,
            })
            prop.action_set_available()
            return prop

        cls.listed = make('Published Penthouse', is_published=True)
        cls.for_sale = make('Published Villa', property_for='sale', sale_price=9000000.0, rent_price=0.0,
                            city='Pune', bedrooms=5, is_published=True)
        cls.unpublished = make('Draft Penthouse')
        cls.rented = make('Rented Penthouse', is_published=True)
        cls.env['property.rental.contract'].create({
            'property_id': cls.rented.id, 'tenant_id': cls.tenant.id,
            'date_start': '2026-01-01', 'date_end': '2026-12-31',
        }).action_start()
        cls.image = cls.env['property.image'].create({'name': 'Terrace', 'image_1920': PNG, 'property_id': cls.listed.id})
        cls.hidden_image = cls.env['property.image'].create({'name': 'Hidden', 'image_1920': PNG, 'property_id': cls.unpublished.id})

    def _get(self, url, **kwargs):
        return self.url_open(url, allow_redirects=kwargs.pop('allow_redirects', True), **kwargs)

    def _csrf(self, html):
        return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

    def _post_enquiry(self, prop, **data):
        page = self._get(prop.website_url)
        payload = {'csrf_token': self._csrf(page.text), 'name': 'Asha Patel', 'email': 'asha@example.com',
                   'phone': '+91 98250 11111', 'message': 'Is it pet friendly?'}
        payload.update(data)
        return self.url_open(f'{prop.website_url}/enquiry', data=payload)

    # ------------------------------------------------------------------
    # Public pages
    # ------------------------------------------------------------------
    def test_listing_shows_only_published_available_properties(self):
        response = self._get('/properties')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Published Penthouse', response.text)
        self.assertIn('Published Villa', response.text)
        self.assertNotIn('Draft Penthouse', response.text)
        self.assertNotIn('Rented Penthouse', response.text)
        self.assertIn('name="viewport"', response.text)
        self.assertIn('col-12 col-sm-6 col-lg-4', response.text)

    def test_detail_page(self):
        response = self._get(self.listed.website_url)
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('Published Penthouse', html)
        self.assertIn('Public text for Published Penthouse', html)
        self.assertIn(f'/properties/gallery/{self.image.id}/image_256', html)
        # Every enquiry field is rendered, the message box included while it is still empty.
        for field in ('name="name"', 'name="email"', 'name="phone"', 'name="message"'):
            self.assertIn(field, html)
        # Never published: internal description, owner, tenants, contracts.
        for secret in ('INTERNAL NOTE', 'Secret Owner Name', 'Hidden Tenant Name', 'RC/'):
            self.assertNotIn(secret, html)

    def test_unpublished_and_unavailable_properties_are_not_reachable(self):
        for prop in (self.unpublished, self.rented):
            with self.subTest(prop=prop.name):
                self.assertEqual(self._get(f'/properties/{prop.id}').status_code, 404)
                self.assertEqual(self._get(f'/properties/image/{prop.id}/image_512').status_code, 404)
        self.assertEqual(self._get('/properties/999999999').status_code, 404)
        self.assertEqual(self._get('/properties/not-a-property').status_code, 404)
        self.assertEqual(self._get(f'/properties/gallery/{self.hidden_image.id}/image_256').status_code, 404)
        self.listed.action_archive()
        self.assertEqual(self._get(f'/properties/{self.listed.id}').status_code, 404)

    def test_images(self):
        self.assertEqual(self._get(f'/properties/image/{self.listed.id}/image_512').status_code, 200)
        self.assertEqual(self._get(f'/properties/gallery/{self.image.id}/image_256').status_code, 200)
        # Only whitelisted image fields can be requested.
        self.assertEqual(self._get(f'/properties/image/{self.listed.id}/image_1920').status_code, 404)
        self.assertEqual(self._get(f'/properties/image/{self.listed.id}/description').status_code, 404)

    def test_other_company_properties_are_hidden(self):
        other = self.env['res.company'].create({'name': 'Other Realty'})
        owner = self.env['res.partner'].create({'name': 'Other owner', 'is_property_owner': True, 'company_id': other.id})
        prop = self.env['property.property'].create({
            'name': 'Other Company Flat', 'type_id': self.listed.type_id.id, 'owner_id': owner.id,
            'rent_price': 1.0, 'company_id': other.id, 'is_published': True,
        })
        prop.action_set_available()
        self.assertNotIn('Other Company Flat', self._get('/properties').text)
        self.assertEqual(self._get(f'/properties/{prop.id}').status_code, 404)

    def test_brochure_link(self):
        self.unpublished.with_user(self.agent).action_generate_brochure_link()
        token = self.unpublished.website_brochure_token
        url = f'/properties/brochure/{self.unpublished.id}/{token}'
        response = self._get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Draft Penthouse', response.text)
        self.assertNotIn('INTERNAL NOTE', response.text)
        self.assertEqual(self._get(f'/properties/image/{self.unpublished.id}/image_512?token={token}').status_code, 200)
        for bad in (f'/properties/brochure/{self.unpublished.id}/{"0" * 32}',
                    f'/properties/brochure/{self.listed.id}/{token}',
                    f'/properties/image/{self.unpublished.id}/image_512?token=wrong'):
            with self.subTest(url=bad):
                self.assertEqual(self._get(bad).status_code, 404)
        # Renewing the link disables the old one.
        self.unpublished.with_user(self.agent).action_generate_brochure_link()
        self.assertEqual(self._get(url).status_code, 404)

    # ------------------------------------------------------------------
    # Search and filters
    # ------------------------------------------------------------------
    def test_search_and_filters(self):
        cases = {
            '/properties?purpose=rent': ({'Published Penthouse'}, {'Published Villa'}),
            '/properties?purpose=sale': ({'Published Villa'}, {'Published Penthouse'}),
            '/properties?search=Villa': ({'Published Villa'}, {'Published Penthouse'}),
            '/properties?city=pune': ({'Published Villa'}, {'Published Penthouse'}),
            '/properties?bedrooms=4': ({'Published Villa'}, {'Published Penthouse'}),
            '/properties?purpose=rent&max_price=20000': (set(), {'Published Penthouse'}),
            '/properties?min_price=1000000': ({'Published Villa'}, {'Published Penthouse'}),
            f'/properties?search={self.listed.code}': ({'Published Penthouse'}, {'Published Villa'}),
        }
        for url, (present, absent) in cases.items():
            with self.subTest(url=url):
                html = self._get(url).text
                for name in present:
                    self.assertIn(name, html)
                for name in absent:
                    self.assertNotIn(name, html)

    def test_invalid_search_parameters_are_ignored(self):
        for url in ('/properties?min_price=abc&bedrooms=lots&type=x&purpose=steal&sort=;drop',
                    '/properties?search=' + 'x' * 5000, '/properties?category=../../etc', '/properties/page/999'):
            with self.subTest(url=url[:60]):
                self.assertEqual(self._get(url).status_code, 200)
        html = self._get('/properties?purpose=steal').text
        self.assertIn('Published Penthouse', html)
        self.assertIn('Published Villa', html)

    # ------------------------------------------------------------------
    # Enquiry form
    # ------------------------------------------------------------------
    def test_enquiry_creates_crm_lead(self):
        response = self._post_enquiry(self.listed)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Your enquiry has been sent', response.text)
        lead = self.env['crm.lead'].search([('property_id', '=', self.listed.id)])
        self.assertEqual(len(lead), 1)
        self.assertEqual(lead.property_for, 'rent')
        self.assertEqual(lead.contact_name, 'Asha Patel')
        self.assertEqual(lead.email_from, 'asha@example.com')
        self.assertEqual(lead.phone, '+91 98250 11111')
        self.assertIn('pet friendly', lead.description)
        self.assertEqual(lead.user_id, self.agent, "Assigned to the property's agent")
        self.assertEqual(lead.medium_id, self.env.ref('utm.utm_medium_website'))
        self.assertTrue(lead.activity_ids, "A follow-up is scheduled")
        self.assertFalse(self.listed.rental_contract_ids, "An enquiry never creates a contract")

    def test_repeat_enquiry_is_added_to_the_open_lead(self):
        self._post_enquiry(self.listed)
        self._post_enquiry(self.listed, email='ASHA@example.com', message='Second question about parking')
        leads = self.env['crm.lead'].search([('property_id', '=', self.listed.id)])
        self.assertEqual(len(leads), 1, "No duplicate lead for the same visitor and property")
        self.assertTrue(any('parking' in (m.body or '') for m in leads.message_ids))

    def test_invalid_enquiries(self):
        for data, field in (({'name': ''}, 'name'), ({'email': 'not-an-email'}, 'email'),
                            ({'phone': '<script>'}, 'phone')):
            with self.subTest(field=field):
                response = self._post_enquiry(self.listed, **data)
                self.assertEqual(response.status_code, 400)
                self.assertIn('is-invalid', response.text)
        self.assertFalse(self.env['crm.lead'].search([('property_id', '=', self.listed.id)]))

    def test_enquiry_input_is_escaped(self):
        self._post_enquiry(self.listed, message='<script>alert(1)</script><b>bold</b>')
        lead = self.env['crm.lead'].search([('property_id', '=', self.listed.id)])
        self.assertNotIn('<script>', lead.description)
        self.assertIn('&lt;script&gt;', lead.description)

    def test_honeypot_and_csrf(self):
        response = self._post_enquiry(self.listed, website_url='http://spam.example')
        self.assertIn('Your enquiry has been sent', response.text, "Bots get no signal")
        self.assertFalse(self.env['crm.lead'].search([('property_id', '=', self.listed.id)]))
        response = self.url_open(f'{self.listed.website_url}/enquiry', data={'name': 'X', 'email': 'x@example.com'})
        self.assertEqual(response.status_code, 400, "Posts without a CSRF token are refused")
        self.assertFalse(self.env['crm.lead'].search([('property_id', '=', self.listed.id)]))

    def test_no_enquiry_on_unpublished_property(self):
        page = self._get(self.listed.website_url)
        response = self.url_open(f'/properties/{self.unpublished.id}/enquiry', data={
            'csrf_token': self._csrf(page.text), 'name': 'Asha', 'email': 'asha@example.com',
        })
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.env['crm.lead'].search([('property_id', '=', self.unpublished.id)]))

    def test_contact_form_creates_lead(self):
        """ The standard Contact Us form (website_crm) creates CRM leads. """
        self.assertTrue(self.env['ir.model'].search([('model', '=', 'crm.lead'), ('website_form_access', '=', True)]))

    # ------------------------------------------------------------------
    # Backend
    # ------------------------------------------------------------------
    def test_only_managers_publish(self):
        with self.assertRaises(AccessError):
            self.unpublished.with_user(self.agent).write({'is_published': True})
        self.assertFalse(self.unpublished.with_user(self.agent).can_publish)
        self.unpublished.with_user(self.manager).write({'is_published': True})
        self.assertTrue(self.unpublished.is_published)
        self.assertEqual(self.unpublished.website_url, f"/properties/{self.env['ir.http']._slug(self.unpublished)}")


@tagged('post_install', '-at_install')
class TestPropertyWebsiteMobile(HttpCase):
    browser_size = '375x667'
    touch_enabled = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ptype = cls.env['property.type'].create({'name': 'Studio P9', 'category': 'residential'})
        owner = cls.env['res.partner'].create({'name': 'Mobile Owner', 'is_property_owner': True})
        cls.prop = cls.env['property.property'].create({
            'name': 'Mobile Studio', 'type_id': ptype.id, 'owner_id': owner.id, 'rent_price': 9000.0,
            'is_published': True, 'image_1920': PNG,
        })
        cls.prop.action_set_available()

    def _check_fits_phone(self, url, selector):
        code = """
            const started = Date.now();
            const timer = setInterval(() => {
                if (document.querySelector(%r)) {
                    clearInterval(timer);
                    const overflow = document.documentElement.scrollWidth - window.innerWidth;
                    if (window.innerWidth > 400) {
                        console.error('Not a phone-sized viewport: ' + window.innerWidth);
                    } else if (overflow > 1) {
                        console.error('Page is wider than the phone screen by ' + overflow + 'px');
                    } else {
                        console.log('test successful');
                    }
                } else if (Date.now() - started > 20000) {
                    clearInterval(timer);
                    console.error('Timed out');
                }
            }, 100);
        """ % selector
        self.browser_js(url, code)

    def test_listing_fits_phone(self):
        self._check_fits_phone('/properties', '.o_property_card')

    def test_detail_fits_phone(self):
        self._check_fits_phone(self.prop.website_url, '#property-request form')
