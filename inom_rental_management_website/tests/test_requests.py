import re

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestPropertyRequests(HttpCase):
    """ Rent and Buy forms on the property page. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(cls.env, 'req_manager', groups='inom_rental_management.group_rental_manager,sales_team.group_sale_salesman_all_leads')
        ptype = cls.env['property.type'].create({'name': 'Flat REQ', 'category': 'residential'})
        owner = cls.env['res.partner'].create({'name': 'Owner REQ', 'is_property_owner': True})

        def make(name, **vals):
            prop = cls.env['property.property'].create({
                'name': name, 'type_id': ptype.id, 'owner_id': owner.id, 'city': 'Pune', 'is_published': True, **vals,
            })
            prop.action_set_available()
            return prop

        cls.for_rent = make('Rent Flat REQ', rent_price=30000.0)
        cls.for_sale = make('Sale Flat REQ', property_for='sale', sale_price=9000000.0)
        cls.today = fields.Date.context_today(cls.env.user)

    def _csrf(self, url):
        return re.search(r'name="csrf_token" value="([^"]+)"', self.url_open(url).text).group(1)

    def _post(self, prop, route, **data):
        payload = {'csrf_token': self._csrf(prop.website_url), 'name': 'Kiran Rao', 'email': 'kiran@example.com',
                   'phone': '+91 98200 12345', 'message': 'Can I visit on Saturday?'}
        payload.update(data)
        return self.url_open(f'{prop.website_url}/{route}', data=payload)

    def _rent(self, prop=None, **data):
        values = {'move_in_date': str(self.today + relativedelta(days=20)), 'lease_months': '12', 'occupants': '3'}
        values.update(data)
        return self._post(prop or self.for_rent, 'rent', **values)

    def _buy(self, prop=None, **data):
        values = {'offer_price': '8,500,000', 'financing': 'loan', 'timeline': '1_3'}
        values.update(data)
        return self._post(prop or self.for_sale, 'buy', **values)

    def _leads(self, prop):
        return self.env['crm.lead'].search([('property_id', '=', prop.id)])

    def test_detail_page_offers_rent_and_buy(self):
        html = self.url_open(self.for_rent.website_url).text
        for tab in ('property_tab_rent', 'property_tab_sale', 'property_tab_enquiry'):
            self.assertIn(tab, html)
        self.assertRegex(html, r'nav-link active"?[^>]*>\s*<i class="fa fa-key', "A rent property opens on the Rent tab")
        self.assertIn('/rent"', html)
        self.assertNotIn('/buy"', html, "No purchase form for a property that is not for sale")
        self.assertIn('This property is only available', html)
        self.assertIn('/properties?purpose=sale&amp;city=Pune&amp;category=residential', html)

        html = self.url_open(self.for_sale.website_url).text
        self.assertIn('/buy"', html)
        self.assertNotIn('/rent"', html)
        self.assertRegex(html, r'nav-link active"?[^>]*>\s*<i class="fa fa-home', "A sale property opens on the Buy tab")

    def test_rent_request_creates_rental_enquiry(self):
        response = self._rent()
        self.assertEqual(response.status_code, 200)
        self.assertIn('Your rent request has been sent', response.text)
        lead = self._leads(self.for_rent)
        self.assertEqual(len(lead), 1)
        self.assertEqual(lead.property_for, 'rent')
        self.assertEqual(lead.property_move_in_date, self.today + relativedelta(days=20))
        self.assertEqual((lead.property_lease_months, lead.property_occupants), (12, 3))
        self.assertEqual(lead.email_from, 'kiran@example.com')
        self.assertIn('Lease length: 12 months', lead.description)
        self.assertIn('Can I visit on Saturday?', lead.description)
        self.assertFalse(self.for_rent.rental_contract_ids, "A request never creates a contract by itself")

    def test_buy_request_creates_sale_enquiry(self):
        response = self._buy()
        self.assertIn('Your purchase request has been sent', response.text)
        lead = self._leads(self.for_sale)
        self.assertEqual(lead.property_for, 'sale')
        self.assertEqual(lead.ask_price, 8500000.0)
        self.assertEqual((lead.property_financing, lead.property_purchase_timeline), ('loan', '1_3'))
        self.assertFalse(self.for_sale.sale_contract_ids)
        # The offer is optional
        self._buy(email='other@example.com', offer_price='')
        self.assertFalse(self._leads(self.for_sale).filtered(lambda l: l.email_from == 'other@example.com').ask_price)

    def test_invalid_requests_show_errors_on_their_tab(self):
        cases = [
            ('rent', {'move_in_date': str(self.today - relativedelta(days=1))}, 'move-in date within the next 12 months'),
            ('rent', {'move_in_date': 'soon'}, 'move-in date within the next 12 months'),
            ('rent', {'lease_months': '7'}, 'Choose a lease length'),
            ('rent', {'occupants': '0'}, 'number of occupants'),
            ('buy', {'offer_price': 'a lot'}, 'Enter your offer as an amount'),
            ('buy', {'financing': 'bitcoin'}, 'how you plan to pay'),
            ('buy', {'timeline': ''}, 'when you would like to buy'),
            ('buy', {'email': 'not-an-email'}, 'valid email address'),
        ]
        for route, data, error in cases:
            with self.subTest(route=route, data=data):
                response = (self._rent if route == 'rent' else self._buy)(**data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(error, response.text)
                tab = 'rent' if route == 'rent' else 'sale'
                self.assertRegex(response.text, rf'show active"?[^>]*id="property_pane_{tab}"|id="property_pane_{tab}"[^>]*show active')
        self.assertFalse(self._leads(self.for_rent) | self._leads(self.for_sale))

    def test_repeat_request_updates_the_open_enquiry(self):
        self._rent()
        self._rent(email='KIRAN@example.com', lease_months='24', occupants='2', message='We would like two parking slots')
        lead = self._leads(self.for_rent)
        self.assertEqual(len(lead), 1, "No duplicate enquiry")
        self.assertEqual((lead.property_lease_months, lead.property_occupants), (24, 2))
        self.assertIn('two parking slots', lead.message_ids[0].body)

    def test_request_for_the_wrong_purpose_or_by_a_bot_is_ignored(self):
        self._buy(prop=self.for_rent)
        self._rent(prop=self.for_sale)
        response = self._rent(website_url='http://spam.example')
        self.assertIn('Your rent request has been sent', response.text, "Bots get no signal")
        self.assertFalse(self._leads(self.for_rent) | self._leads(self.for_sale))

    def test_rental_contract_uses_the_requested_dates(self):
        self._rent(move_in_date=str(self.today + relativedelta(days=10)), lease_months='6')
        lead = self._leads(self.for_rent).with_user(self.manager)
        action = lead.action_create_property_rental()
        contract = self.env['property.rental.contract'].browse(action['res_id'])
        start = self.today + relativedelta(days=10)
        self.assertEqual((contract.date_start, contract.date_end), (start, start + relativedelta(months=6, days=-1)))
        self.assertEqual(contract.state, 'draft')

    def test_tabs_switch_in_the_browser(self):
        code = """
            const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
            const pane = (key) => document.getElementById('property_pane_' + key);
            // Wait until a pane is shown (Bootstrap fades panes in), or give up after 3 seconds.
            async function shown(key) {
                for (let i = 0; i < 30; i++) {
                    if (pane(key).classList.contains('show') && !document.querySelector('.o_property_request .tab-pane.fade.active:not(.show)')) {
                        return true;
                    }
                    await sleep(100);
                }
                return false;
            }
            (async () => {
                if (!await shown('rent')) { return console.error('Rent tab not open first'); }
                document.getElementById('property_tab_sale').click();
                if (!await shown('sale')) { return console.error('Buy tab did not open'); }
                // The link works once the page's scripts have started: click again until it does.
                let opened = false;
                for (let i = 0; i < 20 && !opened; i++) {
                    document.querySelector('.o_property_tab_link').click();
                    opened = await shown('enquiry');
                }
                if (!opened) { return console.error('Ask a question link did not open its tab'); }
                console.log('test successful');
            })();
        """
        self.browser_js(self.for_rent.website_url, code)
