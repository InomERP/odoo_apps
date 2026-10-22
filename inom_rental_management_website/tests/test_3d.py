import base64
import html
import json
import re
import struct

from psycopg2.errors import CheckViolation

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


def make_glb():
    """ A minimal valid GLB (binary glTF 2.0): one triangle. """
    positions = struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
    gltf = {
        'asset': {'version': '2.0'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0}}]}],
        'buffers': [{'byteLength': len(positions)}],
        'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': len(positions)}],
        'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3',
                       'min': [0, 0, 0], 'max': [1, 1, 0]}],
    }
    json_chunk = json.dumps(gltf).encode()
    json_chunk += b' ' * (-len(json_chunk) % 4)
    bin_chunk = positions + b'\0' * (-len(positions) % 4)
    body = (struct.pack('<I4s', len(json_chunk), b'JSON') + json_chunk
            + struct.pack('<I4s', len(bin_chunk), b'BIN\0') + bin_chunk)
    return struct.pack('<4sII', b'glTF', 2, 12 + len(body)) + body


GLB = base64.b64encode(make_glb())


@tagged('post_install', '-at_install')
class TestProperty3DView(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.villa_type = cls.env['property.type'].create({'name': 'Villa 3D', 'category': 'residential'})
        cls.flat_type = cls.env['property.type'].create({'name': 'Flat 3D', 'category': 'residential'})
        cls.shop_type = cls.env['property.type'].create({'name': 'Retail Shop 3D', 'category': 'commercial'})
        cls.plot_type = cls.env['property.type'].create({'name': 'Plot 3D', 'category': 'land'})
        owner = cls.env['res.partner'].create({'name': 'Owner Kept Private 3D', 'is_property_owner': True})

        def make(name, ptype, **vals):
            prop = cls.env['property.property'].create({
                'name': name, 'type_id': ptype.id, 'owner_id': owner.id, 'rent_price': 30000.0,
                'total_area': 1200.0, 'bedrooms': 3, **vals,
            })
            prop.action_set_available()
            return prop

        cls.villa = make('Sunrise Villa 3D', cls.villa_type, is_published=True, land_area=3000.0)
        cls.flat = make('Tower Flat 3D', cls.flat_type, is_published=True, building_floors=14)
        cls.with_model = make('Modelled Flat 3D', cls.flat_type, is_published=True, model_3d=GLB,
                              model_3d_filename='flat.glb')
        cls.hidden = make('Hidden Flat 3D', cls.flat_type, model_3d=GLB, model_3d_filename='hidden.glb')

    def _section(self, prop, url=None):
        page = self.url_open(url or prop.website_url)
        self.assertEqual(page.status_code, 200)
        match = re.search(r'<section[^>]*class="o_property_3d[^"]*"[^>]*>', page.text)
        return match and match.group(0)

    def _spec(self, section):
        return json.loads(html.unescape(re.search(r'data-spec="([^"]*)"', section).group(1)))

    def test_generated_model_spec_on_detail_page(self):
        section = self._section(self.villa)
        self.assertTrue(section, "The detail page has a 3D view")
        self.assertNotIn('data-model-url', section, "No uploaded model: the generated one is used")
        spec = self._spec(section)
        self.assertEqual(spec['kind'], 'house')
        self.assertEqual(spec['floors'], 2, "Typical floors when none are given")
        self.assertAlmostEqual(spec['area'], 111.5, places=1, msg="1200 ft2 in square metres")
        self.assertEqual(set(spec), {'kind', 'floors', 'area', 'land', 'bedrooms', 'bathrooms', 'furnishing', 'interior'},
                         "Only public facts")
        self.assertTrue(spec['interior'])
        page = self.url_open(self.villa.website_url).text
        self.assertIn('Illustrative model', page)
        self.assertNotIn('Owner Kept Private 3D', page)

        flat = self._spec(self._section(self.flat))
        self.assertEqual((flat['kind'], flat['floors']), ('apartment', 14))

    def test_style_detection_and_override(self):
        shop = self.env['property.property'].new({'type_id': self.shop_type.id, 'total_area': 500, 'area_unit': 'sq_m'})
        self.assertEqual(shop._website_3d_spec()['kind'], 'shop')
        plot = self.env['property.property'].new({'type_id': self.plot_type.id})
        self.assertEqual(plot._website_3d_spec()['kind'], 'plot')
        office = self.env['property.property'].new({'type_id': self.flat_type.id, 'building_3d_style': 'office'})
        self.assertEqual(office._website_3d_spec()['kind'], 'office')

    def test_interior_follows_the_property(self):
        plot = self.env['property.property'].new({'type_id': self.plot_type.id})
        self.assertFalse(plot._website_3d_spec()['interior'], "A plot has no interior")
        self.flat.write({'website_3d_interior': False, 'bathrooms': 2, 'furnishing': 'furnished'})
        spec = self._spec(self._section(self.flat))
        self.assertFalse(spec['interior'])
        self.assertEqual((spec['bathrooms'], spec['furnishing']), (2, 'furnished'))

    def test_3d_view_can_be_switched_off(self):
        self.flat.website_show_3d = False
        self.assertFalse(self._section(self.flat))

    def test_uploaded_model_is_served_to_visitors_who_may_see_the_property(self):
        section = self._section(self.with_model)
        self.assertIn(f'data-model-url="/properties/model/{self.with_model.id}"', section)
        self.assertNotIn('Illustrative model', self.url_open(self.with_model.website_url).text)
        response = self.url_open(f'/properties/model/{self.with_model.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'model/gltf-binary')
        self.assertEqual(response.content[:4], b'glTF')
        # Unpublished property, property without a model, 3D view switched off: nothing to see.
        self.assertEqual(self.url_open(f'/properties/model/{self.hidden.id}').status_code, 404)
        self.assertEqual(self.url_open(f'/properties/model/{self.villa.id}').status_code, 404)
        self.with_model.website_show_3d = False
        self.assertEqual(self.url_open(f'/properties/model/{self.with_model.id}').status_code, 404)

    def test_brochure_link_shows_the_model_of_an_unpublished_property(self):
        self.hidden.with_user(self.env.ref('base.user_admin')).action_generate_brochure_link()
        token = self.hidden.sudo().website_brochure_token
        section = self._section(self.hidden, url=f'/properties/brochure/{self.hidden.id}/{token}')
        self.assertIn(f'data-model-url="/properties/model/{self.hidden.id}?token={token}"', section)
        self.assertEqual(self.url_open(f'/properties/model/{self.hidden.id}?token={token}').status_code, 200)
        self.assertEqual(self.url_open(f'/properties/model/{self.hidden.id}?token=wrong').status_code, 404)

    def test_only_glb_files_are_accepted(self):
        for data in (base64.b64encode(b'not a model'), base64.b64encode(b'glTF\x01\x00\x00\x00rest')):
            with self.subTest(data=data[:12]), self.assertRaises(ValidationError):
                self.flat.write({'model_3d': data})
        self.flat.write({'model_3d': GLB})

    def test_floors_range(self):
        with self.assertRaises(CheckViolation), mute_logger('odoo.sql_db'), self.cr.savepoint():
            self.flat.write({'building_floors': 500})
            self.flat.flush_recordset()

    # ------------------------------------------------------------------
    # In the browser
    # ------------------------------------------------------------------
    def _wait_for_3d(self, url, explore=False):
        code = """
            const explore = %s;
            const view = () => document.querySelector('.o_property_3d');
            const fail = (message) => console.error(message);
            const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
            async function exploreInside() {
                view().querySelector('.o_property_3d_mode[data-mode=interior]').click();
                await sleep(800);
                if (view().dataset.mode !== 'interior') { return fail('Interior mode did not open'); }
                const rooms = [...view().querySelectorAll('.o_property_3d_room[data-room]')].map((b) => b.textContent);
                if (!rooms.includes('Living & Dining') || !rooms.some((name) => name.includes('Bedroom'))) {
                    return fail('Rooms missing: ' + rooms.join(', '));
                }
                view().querySelector('.o_property_3d_mode[data-mode=walk]').click();
                await sleep(800);
                const bedroom = [...view().querySelectorAll('.o_property_3d_room[data-room]')].find((b) => b.textContent.includes('Bedroom'));
                bedroom.click();
                await sleep(800);
                window.dispatchEvent(new KeyboardEvent('keydown', {key: 'w'}));
                await sleep(600);
                window.dispatchEvent(new KeyboardEvent('keyup', {key: 'w'}));
                if (view().dataset.mode !== 'walk') { return fail('Walk-through did not open'); }
                view().querySelector('.o_property_3d_mode[data-mode=exterior]').click();
                await sleep(300);
                console.log('test successful');
            }""" % ('true' if explore else 'false') + """
            const started = Date.now();
            const timer = setInterval(() => {
                const view = document.querySelector('.o_property_3d');
                if (!view) {
                    clearInterval(timer);
                    console.error('No 3D view on the page');
                    return;
                }
                view.scrollIntoView();
                const state = view.dataset.state;
                if (state === 'ready') {
                    clearInterval(timer);
                    if (!view.querySelector('canvas.o_property_3d_canvas')) {
                        console.error('3D view ready without a canvas');
                    } else if (explore) {
                        exploreInside();
                    } else {
                        document.querySelector('.o_property_3d_reset').click();
                        document.querySelector('.o_property_3d_rotate').click();
                        console.log('test successful');
                    }
                } else if (state === 'unsupported') {
                    clearInterval(timer);
                    console.log('test successful');  // no WebGL in this browser: the message is shown instead
                } else if (state === 'error' || Date.now() - started > 30000) {
                    clearInterval(timer);
                    console.error('3D view did not load: ' + state);
                }
            }, 200);
        """
        self.browser_js(url, code)

    def test_generated_model_renders_in_the_browser(self):
        self._wait_for_3d(self.villa.website_url)

    def test_interior_can_be_explored_in_the_browser(self):
        self.flat.write({'bedrooms': 2, 'bathrooms': 1, 'furnishing': 'furnished'})
        self._wait_for_3d(self.flat.website_url, explore=True)

    def test_uploaded_model_renders_in_the_browser(self):
        self._wait_for_3d(self.with_model.website_url)
