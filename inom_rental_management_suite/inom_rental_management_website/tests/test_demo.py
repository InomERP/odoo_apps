from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.inom_rental_management_website.models import rental_demo


@tagged('post_install', '-at_install')
class TestWebsiteDemo(TransactionCase):
    """ The demo listings are published by code, so that they are also published when demo data
    reaches an existing database through an upgrade (record overrides of noupdate demo records
    are skipped then). """

    def _demo_property(self, xmlid_name, **vals):
        ptype = self.env['property.type'].create({'name': f'Demo type {xmlid_name}', 'category': 'residential'})
        prop = self.env['property.property'].create(dict({
            'name': xmlid_name, 'type_id': ptype.id, 'rent_price': 1000.0, 'state': 'available',
        }, **vals))
        self.env['ir.model.data'].create({
            'module': 'rental_management_website_test', 'name': xmlid_name,
            'model': 'property.property', 'res_id': prop.id, 'noupdate': True,
        })
        return prop, f'rental_management_website_test.{xmlid_name}'

    def test_demo_listings_published_once(self):
        listed, listed_xmlid = self._demo_property('listed')
        draft, draft_xmlid = self._demo_property('not_ready', state='draft')
        listings = {listed_xmlid: '<p>Demo text</p>', draft_xmlid: '<p>Draft text</p>',
                    'rental_management_website_test.missing': '<p>Gone</p>'}
        with patch.dict(rental_demo.DEMO_LISTINGS, listings, clear=True):
            self.env['property.rental.demo']._load_website_demo()
            self.assertTrue(listed.is_published)
            self.assertIn('Demo text', listed.website_description)
            self.assertFalse(draft.is_published, "Only properties open for rent or sale are published")

            listed.is_published = False
            self.env['property.rental.demo']._load_website_demo()
            self.assertFalse(listed.is_published, "A listing unpublished later stays unpublished on the next upgrade")
