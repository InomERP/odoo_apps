import base64
import binascii
import uuid

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import html_translate

MANAGER_GROUP = 'inom_rental_management.group_rental_manager'
AGENT_GROUP = 'inom_rental_management.group_rental_agent'
MODEL_3D_MAX_BYTES = 50 * 1024 * 1024
# Square metres per area unit, for sizing the generated 3D model.
AREA_TO_M2 = {'sq_ft': 0.092903, 'sq_m': 1.0, 'sq_yd': 0.836127}
DEFAULT_FLOORS = {'apartment': 8, 'office': 6, 'house': 2, 'shop': 2, 'warehouse': 1, 'plot': 0}


class PropertyProperty(models.Model):
    _name = 'property.property'
    _inherit = ['property.property', 'website.published.multi.mixin', 'website.seo.metadata']

    website_description = fields.Html(
        string='Website Description', translate=html_translate, sanitize_overridable=False,
        help="Public description shown on the property page. The internal description is never published.",
    )
    website_show_3d = fields.Boolean(
        string='Show 3D View', default=True,
        help="Show an interactive 3D view on the property page: the uploaded 3D model, or else an illustrative "
             "model generated from the property details.",
    )
    website_3d_interior = fields.Boolean(
        string='Show Interior', default=True,
        help="Let visitors explore the inside: a floor plan with rooms and furniture generated from the bedrooms, "
             "bathrooms, area and furnishing, which they can view from above or walk through.",
    )
    building_3d_style = fields.Selection(
        selection=[
            ('auto', 'Automatic'),
            ('apartment', 'Apartment Building'),
            ('house', 'House / Villa'),
            ('office', 'Office Building'),
            ('shop', 'Shop / Showroom'),
            ('warehouse', 'Warehouse'),
            ('plot', 'Plot of Land'),
        ],
        string='3D Building Style', default='auto', required=True,
        help="Shape of the generated 3D model. Automatic picks it from the property type and category.",
    )
    building_floors = fields.Integer(
        string='Floors in Building',
        help="Number of floors of the building, used for the generated 3D model. Leave 0 to use a typical value.",
    )
    model_3d = fields.Binary(
        string='3D Model', attachment=True, copy=False,
        help="A 3D model of the building in GLB format (binary glTF), shown on the property page. "
             "Most 3D modelling and scanning tools can export GLB.",
    )
    model_3d_filename = fields.Char(string='3D Model File Name', copy=False)
    website_brochure_token = fields.Char(copy=False, readonly=True, groups=AGENT_GROUP)
    website_brochure_url = fields.Char(compute='_compute_website_brochure_url', groups=AGENT_GROUP)

    _building_floors_range = models.Constraint(
        'CHECK(building_floors >= 0 AND building_floors <= 200)',
        'The number of floors must be between 0 and 200.',
    )

    @api.constrains('model_3d')
    def _check_model_3d(self):
        for prop in self.filtered('model_3d'):
            try:
                data = base64.b64decode(prop.model_3d, validate=True)
            except (binascii.Error, ValueError):
                raise ValidationError(self.env._("The 3D model of %(property)s is not a valid file.", property=prop.display_name))
            if len(data) > MODEL_3D_MAX_BYTES:
                raise ValidationError(self.env._(
                    "The 3D model of %(property)s is larger than %(size)s MB.", property=prop.display_name,
                    size=MODEL_3D_MAX_BYTES // (1024 * 1024),
                ))
            # A GLB file starts with the magic "glTF" followed by version 2.
            if data[:4] != b'glTF' or int.from_bytes(data[4:8], 'little') != 2:
                raise ValidationError(self.env._(
                    "Upload the 3D model of %(property)s as a GLB file (binary glTF 2.0).", property=prop.display_name,
                ))

    def _website_3d_kind(self):
        self.ensure_one()
        if self.building_3d_style != 'auto':
            return self.building_3d_style
        type_name = (self.type_id.name or '').lower()
        if self.category == 'land':
            return 'plot'
        if self.category == 'industrial':
            return 'warehouse'
        if self.category == 'commercial':
            shop_words = ('shop', 'retail', 'store', 'showroom', 'outlet', 'kiosk')
            return 'shop' if any(word in type_name for word in shop_words) else 'office'
        house_words = ('villa', 'house', 'bungalow', 'cottage', 'farm', 'duplex', 'row', 'independent')
        return 'house' if any(word in type_name for word in house_words) else 'apartment'

    def _website_3d_spec(self):
        """ What the generated 3D model is built from. Only public facts of the property are used. """
        self.ensure_one()
        kind = self._website_3d_kind()
        to_m2 = AREA_TO_M2.get(self.area_unit, 1.0)
        return {
            'kind': kind,
            'floors': self.building_floors or DEFAULT_FLOORS[kind],
            'area': round((self.total_area or 0.0) * to_m2, 1),
            'land': round((self.land_area or 0.0) * to_m2, 1),
            'bedrooms': self.bedrooms or 0,
            'bathrooms': self.bathrooms or 0,
            'furnishing': self.furnishing or 'unfurnished',
            'interior': bool(self.website_3d_interior) and kind != 'plot',
        }

    @api.depends_context('lang')
    def _compute_website_url(self):
        IrHttp = self.env['ir.http']
        for prop in self:
            prop.website_url = f'/properties/{IrHttp._slug(prop)}' if prop.id else '#'

    def _compute_website_brochure_url(self):
        for prop in self:
            if prop.website_brochure_token:
                prop.website_brochure_url = f'{prop.get_base_url()}/properties/brochure/{prop.id}/{prop.website_brochure_token}'
            else:
                prop.website_brochure_url = False

    @api.depends_context('uid')
    def _compute_can_publish(self):
        """ Only Property Managers approve a property for the website. """
        super()._compute_can_publish()
        if not self.env.user.has_group(MANAGER_GROUP):
            self.can_publish = False

    @api.model
    def _get_can_publish_error_message(self):
        return self.env._("Only Property Managers can publish or unpublish properties on the website.")

    @api.model
    def _website_listing_domain(self, website):
        """ Properties a visitor may see: approved for the website, active, available,
        on this website and in its company. """
        return [
            ('is_published', '=', True),
            ('active', '=', True),
            ('state', '=', 'available'),
            ('company_id', '=', website.company_id.id),
        ] + website.website_domain()

    def action_generate_brochure_link(self):
        """ Create (or renew) the secret link that shows this property's page even when unpublished. """
        self.check_access('write')
        for prop in self:
            prop.sudo().website_brochure_token = uuid.uuid4().hex
        return True
