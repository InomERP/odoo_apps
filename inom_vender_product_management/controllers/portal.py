# -*- coding: utf-8 -*-
"""Vendor-facing portal pages.

Two independent features, each behind its own group (toggled from
Purchase > Settings > Vendor Product Management):

* Vendor Products Portal - the vendor maintains their own catalog.
* Vendor Stocks in Portal - the vendor maintains their own stock levels.

Reads go through the normal ORM so the record rules in security.xml filter
them. Writes are done with sudo on a whitelist of fields, but only after the
record has been fetched WITHOUT sudo, so a vendor can never reach a row that
their record rule would have hidden.
"""
from odoo import fields, http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request
from odoo.http.stream import content_disposition
from odoo.tools import BinaryBytes
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager

PRODUCT_GROUP = 'inom_vender_product_management.group_vendor_product_portal'
STOCK_GROUP = 'inom_vender_product_management.group_vendor_stock_portal'


class VendorProductPortal(portal.CustomerPortal):

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _vendor_partner(self):
        """The partner a portal user acts for. Always the commercial
        partner, so contacts of a vendor company share one catalog."""
        return request.env.user.partner_id.commercial_partner_id

    def _has_product_portal(self):
        return request.env.user.has_group(PRODUCT_GROUP)

    def _has_stock_portal(self):
        return request.env.user.has_group(STOCK_GROUP)

    def _vendor_domain(self):
        return [('vendor_id', '=', self._vendor_partner().id)]

    def _portal_error(self, values, message):
        """Re-render a form with an error banner instead of a 500 page."""
        values['error_message'] = message
        return values

    def _prepare_portal_layout_values(self):
        """Default the variables our breadcrumb extension reads.

        portal_breadcrumbs_vendor_product (see portal_templates.xml) renders
        on every portal page - including plain list pages that use the
        search bar rather than the standalone breadcrumb block - so
        'vendor_product', 'vendor_stock' and 'kind' must always be present,
        not just on the pages that actually set them.
        """
        values = super()._prepare_portal_layout_values()
        values.setdefault('vendor_product', False)
        values.setdefault('vendor_stock', False)
        values.setdefault('kind', False)
        return values

    # ------------------------------------------------------------------
    # /my dashboard counters and cards
    # ------------------------------------------------------------------

    def _prepare_portal_counter_values(self, counter):
        # Odoo 20 computes /my card counters through this hook (Odoo 19 used
        # _prepare_home_portal_values). Same counts: the vendor's own rows,
        # and 0 when the vendor is not in the matching portal group.
        if counter == 'vendor_product_count':
            if not self._has_product_portal():
                return False, False, False
            return 'vendor.product', self._vendor_domain(), 'read'
        if counter == 'vendor_stock_count':
            if not self._has_stock_portal():
                return False, False, False
            return 'vendor.stock', self._vendor_domain(), 'read'
        return super()._prepare_portal_counter_values(counter)

    # ------------------------------------------------------------------
    # Vendor products - list
    # ------------------------------------------------------------------

    def _vendor_product_sortings(self):
        return {
            'name': {'label': "Name", 'order': 'vendor_product_name asc, id asc'},
            'code': {'label': "Reference", 'order': 'vendor_code asc, id asc'},
            'price': {'label': "Price", 'order': 'vendor_price desc, id desc'},
            'date': {'label': "Recently updated", 'order': 'write_date desc, id desc'},
        }

    @http.route(
        ['/my/vendor-products', '/my/vendor-products/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_vendor_products(self, page=1, sortby='name', search='', **kw):
        if not self._has_product_portal():
            return request.redirect('/my')

        VendorProduct = request.env['vendor.product']
        sortings = self._vendor_product_sortings()
        if sortby not in sortings:
            sortby = 'name'

        domain = self._vendor_domain()
        if search:
            domain += ['|',
                       ('vendor_product_name', 'ilike', search),
                       ('vendor_code', 'ilike', search)]

        total = VendorProduct.search_count(domain)
        pager = portal_pager(
            url='/my/vendor-products',
            url_args={'sortby': sortby, 'search': search},
            total=total,
            page=page,
            step=self._items_per_page,
        )
        products = VendorProduct.search(
            domain,
            order=sortings[sortby]['order'],
            limit=self._items_per_page,
            offset=pager['offset'],
        )

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'vendor_product',
            'default_url': '/my/vendor-products',
            'vendor_products': products,
            'pager': pager,
            'searchbar_sortings': sortings,
            'sortby': sortby,
            'search': search,
            'can_import': True,
        })
        return request.render(
            'inom_vender_product_management.portal_my_vendor_products', values
        )

    # ------------------------------------------------------------------
    # Vendor products - create / edit
    # ------------------------------------------------------------------

    def _get_own_vendor_product(self, product_id):
        """Fetch WITHOUT sudo so the record rule decides visibility."""
        product = request.env['vendor.product'].browse(int(product_id))
        product.check_access('read')
        return product

    def _vendor_product_form_values(self, product=None, form=None):
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'vendor_product',
            'vendor_product': product,
            'form': form or {},
            'currency': request.env.company.currency_id,
            'error_message': False,
        })
        return values

    @http.route(
        ['/my/vendor-products/new', '/my/vendor-products/<int:product_id>'],
        type='http', auth='user', website=True,
    )
    def portal_vendor_product_form(self, product_id=None, **kw):
        if not self._has_product_portal():
            return request.redirect('/my')
        product = None
        if product_id:
            try:
                product = self._get_own_vendor_product(product_id)
            except (AccessError, MissingError):
                return request.redirect('/my/vendor-products')
        return request.render(
            'inom_vender_product_management.portal_vendor_product_form',
            self._vendor_product_form_values(product),
        )

    def _parse_vendor_product_form(self, post):
        """Whitelist of what a vendor may set on their own catalog line."""
        name = (post.get('vendor_product_name') or '').strip()
        if not name:
            raise UserError("The product name is required.")
        values = {
            'vendor_product_name': name,
            'vendor_code': (post.get('vendor_code') or '').strip() or False,
            'note': (post.get('note') or '').strip() or False,
        }
        price = (post.get('vendor_price') or '').strip()
        if price:
            try:
                values['vendor_price'] = float(price.replace(',', '.'))
            except ValueError:
                raise UserError("'%s' is not a valid price." % price)
            values['price_outdated'] = False
            values['price_last_updated'] = fields.Datetime.now()
        return values

    @http.route(
        '/my/vendor-products/save', type='http', auth='user',
        website=True, methods=['POST'],
    )
    def portal_vendor_product_save(self, product_id=None, **post):
        if not self._has_product_portal():
            return request.redirect('/my')

        product = None
        if product_id:
            try:
                product = self._get_own_vendor_product(product_id)
            except (AccessError, MissingError):
                return request.redirect('/my/vendor-products')

        try:
            values = self._parse_vendor_product_form(post)
        except UserError as exc:
            return request.render(
                'inom_vender_product_management.portal_vendor_product_form',
                self._portal_error(
                    self._vendor_product_form_values(product, form=post), str(exc)
                ),
            )

        # vendor_id is never taken from the form: it is always the partner
        # behind the session.
        values['vendor_id'] = self._vendor_partner().id
        try:
            # sudo: portal users have no direct write/create rights on
            # vendor.product; safe here because vendor_id is forced to the
            # session's own partner above and record rules are re-checked
            # on every read, so a vendor can never touch another's rows.
            if product:
                product.sudo().write(values)
            else:
                product = request.env['vendor.product'].sudo().create(values)
        except (UserError, ValidationError) as exc:
            return request.render(
                'inom_vender_product_management.portal_vendor_product_form',
                self._portal_error(
                    self._vendor_product_form_values(product, form=post),
                    exc.args[0] if exc.args else str(exc),
                ),
            )
        return request.redirect('/my/vendor-products/%s?message=saved' % product.id)

    # ------------------------------------------------------------------
    # Vendor stocks - list
    # ------------------------------------------------------------------

    def _vendor_stock_sortings(self):
        return {
            'product': {'label': "Product", 'order': 'vendor_product_id asc, id asc'},
            'location': {'label': "Location", 'order': 'location_id asc, id asc'},
            'quantity': {'label': "Quantity", 'order': 'quantity desc, id desc'},
            'date': {'label': "Recently updated", 'order': 'last_updated desc, id desc'},
        }

    @http.route(
        ['/my/vendor-stocks', '/my/vendor-stocks/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_vendor_stocks(self, page=1, sortby='product', search='', **kw):
        if not self._has_stock_portal():
            return request.redirect('/my')

        VendorStock = request.env['vendor.stock']
        sortings = self._vendor_stock_sortings()
        if sortby not in sortings:
            sortby = 'product'

        domain = self._vendor_domain()
        if search:
            domain += ['|',
                       ('vendor_product_id.vendor_product_name', 'ilike', search),
                       ('location_id.name', 'ilike', search)]

        total = VendorStock.search_count(domain)
        pager = portal_pager(
            url='/my/vendor-stocks',
            url_args={'sortby': sortby, 'search': search},
            total=total,
            page=page,
            step=self._items_per_page,
        )
        stocks = VendorStock.search(
            domain,
            order=sortings[sortby]['order'],
            limit=self._items_per_page,
            offset=pager['offset'],
        )

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'vendor_stock',
            'default_url': '/my/vendor-stocks',
            'vendor_stocks': stocks,
            'pager': pager,
            'searchbar_sortings': sortings,
            'sortby': sortby,
            'search': search,
        })
        return request.render(
            'inom_vender_product_management.portal_my_vendor_stocks', values
        )

    # ------------------------------------------------------------------
    # Vendor stocks - create / edit
    # ------------------------------------------------------------------

    def _get_own_vendor_stock(self, stock_id):
        stock = request.env['vendor.stock'].browse(int(stock_id))
        stock.check_access('read')
        return stock

    def _vendor_stock_form_values(self, stock=None, form=None):
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'vendor_stock',
            'vendor_stock': stock,
            'form': form or {},
            # Both lists are read WITHOUT sudo, so the record rules keep
            # them scoped to this vendor.
            'vendor_products': request.env['vendor.product'].search(
                self._vendor_domain(), order='vendor_product_name'
            ),
            'vendor_locations': request.env['vendor.location'].search(
                self._vendor_domain(), order='name'
            ),
            # uom.uom carries no per-vendor data, so a sudo read is the
            # simplest way to offer the dropdown. The list is bounded with
            # a generous limit (well above any realistic UoM count) purely
            # as a safety net against an unbounded load on very large
            # databases; it does not truncate the dropdown in practice.
            # sudo: read-only list of units of measure (no vendor data).
            'uoms': request.env['uom.uom'].sudo().search(
                [], order='name', limit=1000
            ),
            'error_message': False,
        })
        return values

    @http.route(
        ['/my/vendor-stocks/new', '/my/vendor-stocks/<int:stock_id>'],
        type='http', auth='user', website=True,
    )
    def portal_vendor_stock_form(self, stock_id=None, **kw):
        if not self._has_stock_portal():
            return request.redirect('/my')
        stock = None
        if stock_id:
            try:
                stock = self._get_own_vendor_stock(stock_id)
            except (AccessError, MissingError):
                return request.redirect('/my/vendor-stocks')
        return request.render(
            'inom_vender_product_management.portal_vendor_stock_form',
            self._vendor_stock_form_values(stock),
        )

    def _resolve_portal_location(self, post):
        """Either an existing location of this vendor, or a new one created
        from the free-text field on the form."""
        VendorLocation = request.env['vendor.location']
        new_name = (post.get('new_location_name') or '').strip()
        if new_name:
            existing = VendorLocation.search(
                self._vendor_domain() + [('name', '=', new_name)], limit=1
            )
            if existing:
                return existing
            # sudo: portal users have no direct create rights on
            # vendor.location; safe because vendor_id is forced to the
            # session's own partner right here.
            return VendorLocation.sudo().create({
                'vendor_id': self._vendor_partner().id,
                'name': new_name,
            })
        location_id = post.get('location_id')
        if not location_id:
            raise UserError("Pick a location, or type the name of a new one.")
        location = VendorLocation.browse(int(location_id))
        location.check_access('read')
        return location

    def _parse_vendor_stock_form(self, post, stock=None):
        VendorProduct = request.env['vendor.product']

        if stock:
            vendor_product = stock.vendor_product_id
        else:
            product_id = post.get('vendor_product_id')
            if not product_id:
                raise UserError("Pick one of your products.")
            vendor_product = VendorProduct.browse(int(product_id))
            vendor_product.check_access('read')

        quantity = (post.get('quantity') or '').strip()
        if not quantity:
            raise UserError("The quantity is required.")
        try:
            quantity = float(quantity.replace(',', '.'))
        except ValueError:
            raise UserError("'%s' is not a valid quantity." % quantity)

        location = stock.location_id if stock else self._resolve_portal_location(post)

        uom_id = post.get('uom_id')
        if uom_id:
            uom_id = int(uom_id)
        else:
            # sudo: only reading the linked internal product's UoM to use
            # as a default; the portal user already passed the read-access
            # check on vendor_product above.
            uom_id = vendor_product.sudo().product_id.uom_id.id
        if not uom_id:
            raise UserError("Pick a unit of measure.")

        return {
            'vendor_product_id': vendor_product.id,
            'location_id': location.id,
            'quantity': quantity,
            'uom_id': uom_id,
            'note': (post.get('note') or '').strip() or False,
            'last_updated': fields.Datetime.now(),
            'active': True,
        }

    @http.route(
        '/my/vendor-stocks/save', type='http', auth='user',
        website=True, methods=['POST'],
    )
    def portal_vendor_stock_save(self, stock_id=None, **post):
        if not self._has_stock_portal():
            return request.redirect('/my')

        stock = None
        if stock_id:
            try:
                stock = self._get_own_vendor_stock(stock_id)
            except (AccessError, MissingError):
                return request.redirect('/my/vendor-stocks')

        try:
            values = self._parse_vendor_stock_form(post, stock)
            # sudo: portal users have no direct write/create rights on
            # vendor.stock; safe because vendor_product_id/location_id are
            # resolved above through the portal user's own scoped
            # searches, so the vendor implied by the stock line can only
            # ever be the session's own partner.
            if stock:
                stock.sudo().write(values)
            else:
                stock = request.env['vendor.stock'].sudo().create(values)
        except (AccessError, MissingError):
            return request.redirect('/my/vendor-stocks')
        except (UserError, ValidationError) as exc:
            return request.render(
                'inom_vender_product_management.portal_vendor_stock_form',
                self._portal_error(
                    self._vendor_stock_form_values(stock, form=post),
                    exc.args[0] if exc.args else str(exc),
                ),
            )
        return request.redirect('/my/vendor-stocks/%s?message=saved' % stock.id)

    # ------------------------------------------------------------------
    # Import templates and portal imports
    # ------------------------------------------------------------------

    def _may_import(self, kind):
        return self._has_product_portal() if kind == 'product' else self._has_stock_portal()

    @http.route(
        '/my/vendor-import-template/<string:kind>', type='http',
        auth='user', website=False,
    )
    def portal_download_import_template(self, kind, **kw):
        """Serve the configured template with sudo.

        Going through the ORM here rather than /web/content means an admin
        who forgets to tick 'public' on their own attachment does not
        silently break the vendor's portal.
        """
        if kind not in ('product', 'stock') or not self._may_import(kind):
            return request.not_found()
        attachment = request.env['vendor.import.settings'].get_template_attachment(kind)
        if not attachment or not attachment.raw:
            return request.not_found()
        data = attachment.raw.content
        return request.make_response(data, headers=[
            ('Content-Type', attachment.mimetype or 'application/octet-stream'),
            ('Content-Disposition', content_disposition(attachment.name)),
            ('Content-Length', len(data)),
        ])

    def _import_page_values(self, kind, **extra):
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'vendor_product' if kind == 'product' else 'vendor_stock',
            'kind': kind,
            'help_html': request.env['vendor.import.settings'].get_help_html(kind),
            'template_url': '/my/vendor-import-template/%s' % kind,
            'stats': None,
            'error_message': False,
        })
        values.update(extra)
        return values

    def _run_portal_import(self, kind, post):
        """Feed the uploaded file to the very same wizard the backend uses.

        The wizard runs with sudo because it writes vendor.product /
        vendor.location / vendor.stock rows, but vendor_id is pinned to the
        session's partner, so it can only ever touch this vendor's data.
        """
        upload = post.get('import_file')
        if not upload or not upload.filename:
            raise UserError("Please choose a file to upload.")

        model = ('vendor.product.import.wizard' if kind == 'product'
                 else 'vendor.stock.import.wizard')
        values = {
            'vendor_id': self._vendor_partner().id,
            'import_file': BinaryBytes(upload.read()),
            'import_filename': upload.filename,
            'import_only_chosen_lines': bool(post.get('import_only_chosen_lines')),
            'archive_other_products': bool(post.get('archive_other_products')),
        }
        if kind == 'product':
            values['mark_previous_prices_outdated'] = bool(
                post.get('mark_previous_prices_outdated')
            )
        else:
            values['archive_previous_stocks'] = bool(post.get('archive_previous_stocks'))

        # sudo: portal users have no access to the import wizards; safe
        # because vendor_id above is always the session's own partner, so
        # the import can only create/update this vendor's own rows.
        wizard = request.env[model].sudo().create(values)
        return wizard._run_import()

    @http.route(
        '/my/vendor-products/import', type='http', auth='user',
        website=True, methods=['GET', 'POST'],
    )
    def portal_vendor_product_import(self, **post):
        if not self._has_product_portal():
            return request.redirect('/my')
        if request.httprequest.method == 'GET':
            return request.render(
                'inom_vender_product_management.portal_vendor_import',
                self._import_page_values('product'),
            )
        try:
            stats = self._run_portal_import('product', post)
        except (UserError, ValidationError) as exc:
            return request.render(
                'inom_vender_product_management.portal_vendor_import',
                self._import_page_values(
                    'product', error_message=exc.args[0] if exc.args else str(exc)
                ),
            )
        return request.render(
            'inom_vender_product_management.portal_vendor_import',
            self._import_page_values('product', stats=stats),
        )

    @http.route(
        '/my/vendor-stocks/import', type='http', auth='user',
        website=True, methods=['GET', 'POST'],
    )
    def portal_vendor_stock_import(self, **post):
        if not self._has_stock_portal():
            return request.redirect('/my')
        if request.httprequest.method == 'GET':
            return request.render(
                'inom_vender_product_management.portal_vendor_import',
                self._import_page_values('stock'),
            )
        try:
            stats = self._run_portal_import('stock', post)
        except (UserError, ValidationError) as exc:
            return request.render(
                'inom_vender_product_management.portal_vendor_import',
                self._import_page_values(
                    'stock', error_message=exc.args[0] if exc.args else str(exc)
                ),
            )
        return request.render(
            'inom_vender_product_management.portal_vendor_import',
            self._import_page_values('stock', stats=stats),
        )
