import json
import re
from datetime import date

from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import NotFound

from odoo import fields, http
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.mail import plaintext2html, single_email_re

PROPERTIES_PER_PAGE = 12
IMAGE_SIZES = ('image_256', 'image_512', 'image_1024')
PHONE_RE = re.compile(r'^[0-9+()\-.\s]{6,20}$')
SORTS = {
    'newest': 'create_date desc, id desc',
    'name': 'name asc, id asc',
    'price_asc': None,   # depends on the purpose filter
    'price_desc': None,
}
LEASE_MONTHS = (6, 11, 12, 24, 36)
FINANCING = ('cash', 'loan', 'undecided')
TIMELINES = ('now', '1_3', '3_6', 'later')
REQUESTS = ('rent', 'sale', 'enquiry')
FILTER_KEYS = ('search', 'purpose', 'category', 'type', 'city', 'bedrooms', 'min_price', 'max_price', 'sort')


def _clean_text(value, max_length):
    return value.strip()[:max_length] if isinstance(value, str) else ''


def _clean_int(value, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


def _clean_amount(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number < 1e12 else None


class PropertyWebsite(http.Controller):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _listing_domain(self):
        return request.env['property.property']._website_listing_domain(request.website)

    def _get_listed_property(self, property_id):
        """ The property only if a visitor may see it; never reveals whether others exist. """
        prop = request.env['property.property'].sudo().search(
            [('id', '=', property_id)] + self._listing_domain(), limit=1,
        )
        if not prop:
            raise NotFound()
        return prop

    def _get_property_from_slug(self, slug):
        _name, property_id = request.env['ir.http']._unslug(slug)
        if not property_id:
            raise NotFound()
        return self._get_listed_property(property_id)

    def _get_brochure_property(self, property_id, token):
        prop = request.env['property.property'].sudo().browse(property_id).exists()
        if not prop or not prop.active or prop.state == 'sold' or not prop.website_brochure_token \
                or not token or not consteq(prop.website_brochure_token, token):
            raise NotFound()
        return prop

    def _parse_filters(self, params):
        purpose = params.get('purpose') if params.get('purpose') in ('rent', 'sale') else ''
        categories = dict(request.env['property.type']._fields['category'].selection)
        filters = {
            'search': _clean_text(params.get('search'), 100),
            'purpose': purpose,
            'category': params.get('category') if params.get('category') in categories else '',
            'type': _clean_int(params.get('type'), 1, 2**31 - 1),
            'city': _clean_text(params.get('city'), 64),
            'bedrooms': _clean_int(params.get('bedrooms'), 1, 20),
            'min_price': _clean_amount(params.get('min_price')),
            'max_price': _clean_amount(params.get('max_price')),
            'sort': params.get('sort') if params.get('sort') in SORTS else 'newest',
        }
        return filters

    def _filter_domain(self, filters):
        domain = []
        if filters['search']:
            term = filters['search']
            domain += ['|', '|', '|', ('name', 'ilike', term), ('code', 'ilike', term),
                       ('city', 'ilike', term), ('type_id.name', 'ilike', term)]
        if filters['purpose']:
            domain.append(('property_for', '=', filters['purpose']))
        if filters['category']:
            domain.append(('category', '=', filters['category']))
        if filters['type']:
            domain.append(('type_id', '=', filters['type']))
        if filters['city']:
            domain.append(('city', '=ilike', filters['city']))
        if filters['bedrooms']:
            domain.append(('bedrooms', '>=', filters['bedrooms']))
        for key, operator in (('min_price', '>='), ('max_price', '<=')):
            amount = filters[key]
            if amount is None:
                continue
            if filters['purpose'] == 'rent':
                domain.append(('rent_price', operator, amount))
            elif filters['purpose'] == 'sale':
                domain.append(('sale_price', operator, amount))
            else:
                domain += ['|', '&', ('property_for', '=', 'rent'), ('rent_price', operator, amount),
                           '&', ('property_for', '=', 'sale'), ('sale_price', operator, amount)]
        return domain

    def _order(self, filters):
        if filters['sort'] in ('price_asc', 'price_desc') and filters['purpose']:
            field = 'rent_price' if filters['purpose'] == 'rent' else 'sale_price'
            return f"{field} {'asc' if filters['sort'] == 'price_asc' else 'desc'}, id desc"
        return SORTS.get(filters['sort']) or SORTS['newest']

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    @http.route(['/properties', '/properties/page/<int:page>'], type='http', auth='public', website=True, sitemap=True)
    def properties(self, page=1, **params):
        filters = self._parse_filters(params)
        base_domain = self._listing_domain()
        Property = request.env['property.property'].sudo()
        domain = base_domain + self._filter_domain(filters)
        total = Property.search_count(domain)
        url_args = {k: v for k, v in filters.items() if v not in (None, '') and not (k == 'sort' and v == 'newest')}
        pager = request.website.pager(
            url='/properties', total=total, page=page, step=PROPERTIES_PER_PAGE, url_args=url_args,
        )
        properties = Property.search(domain, limit=PROPERTIES_PER_PAGE, offset=pager['offset'], order=self._order(filters))
        type_ids = [ptype.id for [ptype] in Property._read_group(base_domain, ['type_id'])]
        return request.render('inom_rental_management_website.property_listing', {
            'properties': properties,
            'pager': pager,
            'total': total,
            'filters': filters,
            'property_types': request.env['property.type'].sudo().browse(type_ids).sorted('name'),
            'categories': request.env['property.type']._fields['category']._description_selection(request.env),
            'image_url': self._image_url,
        })

    @http.route('/properties/<string:slug>', type='http', auth='public', website=True, sitemap=False)
    def property_detail(self, slug, **params):
        prop = self._get_property_from_slug(slug)
        sent = params.get('request') if params.get('request') in REQUESTS else ('enquiry' if params.get('enquiry') == 'sent' else None)
        return self._render_detail(prop, request_sent=sent)

    @http.route('/properties/brochure/<int:property_id>/<string:token>', type='http', auth='public', website=True,
                sitemap=False)
    def property_brochure(self, property_id, token, **params):
        prop = self._get_brochure_property(property_id, token)
        return self._render_detail(prop, brochure_token=token)

    def _render_detail(self, prop, request_sent=None, errors=None, values=None, brochure_token=None, active_tab=None):
        # The tab opened first: the form just sent or with errors, else the property's own purpose.
        tab = active_tab or request_sent or prop.property_for
        values = {
            'prop': prop,
            'images': prop.image_ids.sorted('sequence'),
            'amenities': prop.amenity_ids,
            'enquiry_sent': request_sent == 'enquiry',
            'request_sent': request_sent,
            'active_tab': tab,
            'today': fields.Date.context_today(prop),
            'max_move_in': fields.Date.context_today(prop) + relativedelta(years=1),
            'lease_months': LEASE_MONTHS,
            'other_purpose_url': self._other_purpose_url(prop),
            'errors': errors or {},
            'values': values or {},
            'brochure_token': brochure_token,
            'listed': bool(prop.filtered_domain(self._listing_domain())),
            'image_url': self._image_url,
            'view_3d': self._view_3d_values(prop, brochure_token),
        }
        if not brochure_token:
            # Published page: lets managers edit and publish it from the website editor.
            values['main_object'] = prop
        return request.render('inom_rental_management_website.property_detail', values, status=400 if errors else 200)

    def _other_purpose_url(self, prop):
        """ Listing of similar properties offered the other way (for sale when this one is for rent). """
        other = 'sale' if prop.property_for == 'rent' else 'rent'
        params = {'purpose': other}
        if prop.city:
            params['city'] = prop.city
        if prop.category:
            params['category'] = prop.category
        return '/properties?' + '&'.join(f'{key}={value}' for key, value in params.items()).replace(' ', '+')

    def _has_model_3d(self, prop):
        return bool(request.env['ir.attachment'].sudo().search_count([
            ('res_model', '=', 'property.property'), ('res_id', '=', prop.id), ('res_field', '=', 'model_3d'),
        ], limit=1))

    def _view_3d_values(self, prop, token=None):
        """ What the property page's 3D view shows: the uploaded model, or else a model generated from the
        property's public details. None when the 3D view is switched off for the property. """
        if not prop.website_show_3d:
            return None
        url = f'/properties/model/{prop.id}'
        return {
            'model_url': (f'{url}?token={token}' if token else url) if self._has_model_3d(prop) else False,
            'spec': json.dumps(prop._website_3d_spec()),
        }

    def _image_url(self, record, size='image_512', token=None):
        if record._name == 'property.image':
            url = f'/properties/gallery/{record.id}/{size}'
        else:
            url = f'/properties/image/{record.id}/{size}'
        return f'{url}?token={token}' if token else url

    # ------------------------------------------------------------------
    # Images: served only for properties a visitor may see
    # ------------------------------------------------------------------
    def _image_response(self, record, size):
        stream = request.env['ir.binary']._get_image_stream_from(record, size)
        return stream.get_response(max_age=3600)

    def _check_visible(self, prop, token):
        if prop.filtered_domain(self._listing_domain()):
            return True
        return bool(token and prop.active and prop.website_brochure_token and consteq(prop.website_brochure_token, token))

    @http.route('/properties/image/<int:property_id>/<string:size>', type='http', auth='public', website=True,
                sitemap=False)
    def property_image(self, property_id, size, token=None, **params):
        prop = request.env['property.property'].sudo().browse(property_id).exists()
        if size not in IMAGE_SIZES or not prop or not self._check_visible(prop, token):
            raise NotFound()
        return self._image_response(prop, size)

    @http.route('/properties/gallery/<int:image_id>/<string:size>', type='http', auth='public', website=True,
                sitemap=False)
    def property_gallery_image(self, image_id, size, token=None, **params):
        image = request.env['property.image'].sudo().browse(image_id).exists()
        if size not in IMAGE_SIZES or not image or not self._check_visible(image.property_id, token):
            raise NotFound()
        return self._image_response(image, size)

    @http.route('/properties/model/<int:property_id>', type='http', auth='public', website=True, sitemap=False)
    def property_model_3d(self, property_id, token=None, **params):
        """ The uploaded 3D model (GLB), served like the pictures: only for a property the visitor may see. """
        prop = request.env['property.property'].sudo().browse(property_id).exists()
        if not prop or not prop.website_show_3d or not self._check_visible(prop, token) \
                or not self._has_model_3d(prop):
            raise NotFound()
        stream = request.env['ir.binary']._get_stream_from(prop, 'model_3d', filename=f'{prop.code or prop.id}.glb',
                                                         mimetype='model/gltf-binary')
        return stream.get_response(max_age=3600)

    # ------------------------------------------------------------------
    # Enquiry form
    # ------------------------------------------------------------------
    def _validate_enquiry(self, post):
        values = {
            'name': _clean_text(post.get('name'), 100),
            'email': _clean_text(post.get('email'), 254),
            'phone': _clean_text(post.get('phone'), 20),
            'message': _clean_text(post.get('message'), 2000),
        }
        errors = {}
        if len(values['name']) < 2:
            errors['name'] = request.env._("Please enter your name.")
        if not single_email_re.match(values['email']):
            errors['email'] = request.env._("Please enter a valid email address.")
        if values['phone'] and not PHONE_RE.match(values['phone']):
            errors['phone'] = request.env._("Please enter a valid phone number.")
        return values, errors

    @http.route('/properties/<string:slug>/enquiry', type='http', auth='public', website=True, methods=['POST'],
                sitemap=False)
    def property_enquiry(self, slug, **post):
        prop = self._get_property_from_slug(slug)
        detail_url = f"/properties/{request.env['ir.http']._slug(prop)}"
        # Honeypot: humans leave this hidden field empty.
        if post.get('website_url'):
            return request.redirect(f'{detail_url}?request=enquiry#property-request')
        values, errors = self._validate_enquiry(post)
        if errors:
            return self._render_detail(prop, errors=errors, values=values, active_tab='enquiry')
        self._record_enquiry(prop, values)
        return request.redirect(f'{detail_url}?request=enquiry#property-request')

    # ------------------------------------------------------------------
    # Rent and buy requests
    # ------------------------------------------------------------------
    def _parse_date(self, value):
        try:
            return date.fromisoformat(value) if isinstance(value, str) and value else None
        except ValueError:
            return None

    def _validate_rent(self, prop, post):
        values, errors = self._validate_enquiry(post)
        today = fields.Date.context_today(prop)
        move_in = self._parse_date(post.get('move_in_date'))
        months = _clean_int(post.get('lease_months'), 1, 120)
        occupants = _clean_int(post.get('occupants'), 1, 50)
        values.update(move_in_date=post.get('move_in_date') or '', lease_months=months, occupants=occupants)
        if not move_in or not today <= move_in <= today + relativedelta(years=1):
            errors['move_in_date'] = request.env._("Choose a move-in date within the next 12 months.")
        if months not in LEASE_MONTHS:
            errors['lease_months'] = request.env._("Choose a lease length.")
        if occupants is None:
            errors['occupants'] = request.env._("Enter the number of occupants (1 to 50).")
        values['move_in'] = move_in
        return values, errors

    def _validate_buy(self, prop, post):
        values, errors = self._validate_enquiry(post)
        offer_text = _clean_text(post.get('offer_price'), 20).replace(',', '')
        offer = _clean_amount(offer_text) if offer_text else None
        values.update(offer_price=post.get('offer_price') or '', offer=offer,
                      financing=post.get('financing'), timeline=post.get('timeline'))
        if offer_text and not offer:
            errors['offer_price'] = request.env._("Enter your offer as an amount, or leave it empty.")
        if values['financing'] not in FINANCING:
            errors['financing'] = request.env._("Tell us how you plan to pay.")
        if values['timeline'] not in TIMELINES:
            errors['timeline'] = request.env._("Tell us when you would like to buy.")
        return values, errors

    def _property_request(self, slug, post, purpose):
        prop = self._get_property_from_slug(slug)
        detail_url = f"/properties/{request.env['ir.http']._slug(prop)}"
        if prop.property_for != purpose:
            # The property is not offered this way: back to its page, on the right tab.
            return request.redirect(f'{detail_url}#property-request')
        if post.get('website_url'):  # honeypot
            return request.redirect(f'{detail_url}?request={purpose}#property-request')
        values, errors = (self._validate_rent if purpose == 'rent' else self._validate_buy)(prop, post)
        if errors:
            return self._render_detail(prop, errors=errors, values=values, active_tab=purpose)
        self._record_request(prop, purpose, values)
        return request.redirect(f'{detail_url}?request={purpose}#property-request')

    @http.route('/properties/<string:slug>/rent', type='http', auth='public', website=True, methods=['POST'],
                sitemap=False)
    def property_rent_request(self, slug, **post):
        return self._property_request(slug, post, 'rent')

    @http.route('/properties/<string:slug>/buy', type='http', auth='public', website=True, methods=['POST'],
                sitemap=False)
    def property_buy_request(self, slug, **post):
        return self._property_request(slug, post, 'sale')

    def _request_summary(self, prop, purpose, values, lead_fields):
        """ The request as text lines, for the enquiry notes and the chatter. """
        Lead = request.env['crm.lead']
        selection = lambda name: dict(Lead._fields[name]._description_selection(request.env))
        if purpose == 'rent':
            lines = [
                request.env._("Preferred move-in date: %(date)s", date=values['move_in'].strftime('%d %b %Y')),
                request.env._("Lease length: %(months)s months", months=values['lease_months']),
                request.env._("Occupants: %(count)s", count=values['occupants']),
            ]
        else:
            offer = (prop.currency_id.format(values['offer']) if values['offer']
                     else request.env._("no offer yet"))
            lines = [
                request.env._("Offer: %(offer)s (listed at %(price)s)", offer=offer, price=prop.currency_id.format(prop.sale_price)),
                request.env._("Financing: %(financing)s", financing=selection('property_financing')[lead_fields['property_financing']]),
                request.env._("Timeline: %(timeline)s", timeline=selection('property_purchase_timeline')[lead_fields['property_purchase_timeline']]),
            ]
        lines.append(request.env._("Phone: %(phone)s", phone=values['phone'] or '-'))
        if values['message']:
            lines += ['', values['message']]
        return '\n'.join(lines)

    def _record_request(self, prop, purpose, values):
        """ A rent or purchase request becomes a CRM enquiry with the details filled in. A repeat request
        from the same visitor updates their open enquiry for this property instead of creating another. """
        Lead = request.env['crm.lead'].sudo()
        if purpose == 'rent':
            lead_fields = {
                'property_move_in_date': values['move_in'],
                'property_lease_months': values['lease_months'],
                'property_occupants': values['occupants'],
            }
            title = request.env._("Rent request: %(property)s", property=prop.display_name)
        else:
            lead_fields = {
                'property_financing': values['financing'],
                'property_purchase_timeline': values['timeline'],
            }
            if values['offer']:
                lead_fields['ask_price'] = values['offer']
            title = request.env._("Purchase request: %(property)s", property=prop.display_name)
        summary = self._request_summary(prop, purpose, values, lead_fields)
        existing = Lead._find_open_property_enquiries(prop, purpose, False, values['email'])[:1]
        if existing:
            existing.write(lead_fields)
            existing.message_post(
                body=plaintext2html(request.env._("New %(kind)s from %(name)s:", kind=title.split(':')[0].lower(),
                                                  name=values['name']) + '\n' + summary),
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
            return existing
        medium = request.env.ref('utm.utm_medium_website', raise_if_not_found=False)
        return Lead.create(dict(lead_fields, **{
            'name': title,
            'type': 'opportunity',
            'property_id': prop.id,
            'property_for': purpose,
            'contact_name': values['name'],
            'email_from': values['email'],
            'phone': values['phone'],
            'description': plaintext2html(summary),
            'company_id': prop.company_id.id,
            'medium_id': medium.id if medium else False,
        }))

    def _record_enquiry(self, prop, values):
        """ Add the message to the visitor's open enquiry for this property, or create one. """
        Lead = request.env['crm.lead'].sudo()
        body = plaintext2html(values['message']) if values['message'] else ''
        existing = Lead._find_open_property_enquiries(prop, prop.property_for, False, values['email'])[:1]
        if existing:
            existing.message_post(
                body=request.env._("New website enquiry from %(name)s (%(phone)s):", name=values['name'],
                                   phone=values['phone'] or '-') + body,
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
            return existing
        medium = request.env.ref('utm.utm_medium_website', raise_if_not_found=False)
        return Lead.create({
            'name': request.env._("Website enquiry: %(property)s", property=prop.display_name),
            'type': 'opportunity',
            'property_id': prop.id,
            'property_for': prop.property_for,
            'contact_name': values['name'],
            'email_from': values['email'],
            'phone': values['phone'],
            'description': body,
            'company_id': prop.company_id.id,
            'medium_id': medium.id if medium else False,
        })
