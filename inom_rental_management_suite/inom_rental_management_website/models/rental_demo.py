from odoo import api, models
from odoo.tools import is_html_empty

# Demo listings published on the website, with their public description.
DEMO_LISTINGS = {
    'inom_rental_management.demo_property_park_view_7':
        "<p>Spacious two-bedroom flat with city views, a modular kitchen and covered parking. "
        "Five minutes from the metro.</p>",
    'inom_rental_management.demo_property_tech_park':
        "<p>Fully furnished office floor for up to 60 seats, with meeting rooms, a cafeteria and power backup.</p>",
    'inom_rental_management.demo_property_park_view_12':
        "<p>Corner three-bedroom apartment on the twelfth floor, ready to move in, "
        "with clubhouse and gym access.</p>",
}


class PropertyRentalDemo(models.AbstractModel):
    _inherit = 'property.rental.demo'

    @api.model
    def _load_website_demo(self):
        """ Publish the demo listings. Done in code rather than by overriding the core demo records,
        because an upgrade skips overrides of records marked noupdate, which demo records are: demo
        data added to an existing database would otherwise stay unpublished. A property that already
        has a website description was handled before, so a listing unpublished later stays unpublished. """
        for xmlid, description in DEMO_LISTINGS.items():
            prop = self.env.ref(xmlid, raise_if_not_found=False)
            if prop and prop.state == 'available' and not prop.is_published and is_html_empty(prop.website_description):
                prop.write({'is_published': True, 'website_description': description})
