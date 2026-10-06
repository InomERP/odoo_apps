# -*- coding: utf-8 -*-
import io

from odoo import api, models, fields
from odoo.exceptions import UserError

try:
    from openpyxl import load_workbook, Workbook
except ImportError:  # pragma: no cover - openpyxl ships with Odoo
    load_workbook = None
    Workbook = None

TEMPLATE_HEADERS = [
    'Import (Yes/No)',
    'Vendor Product Code',
    'Vendor Location',
    'Quantity',
    'Vendor UoM',
    'Notes',
]

TRUE_VALUES = {'yes', 'y', 'true', '1', 'x'}


class VendorStockImportWizard(models.TransientModel):
    _name = 'vendor.stock.import.wizard'
    _description = 'Import Vendor Stocks'

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        ondelete='restrict',
        domain=[('supplier_rank', '>', 0)],
    )
    import_file = fields.Binary(
        string='Table to import',
        required=True,
        help="Upload a filled-in copy of the predefined Vendor Stocks "
             "template (see the Help tab).",
    )
    import_filename = fields.Char(string='Filename')

    import_only_chosen_lines = fields.Boolean(
        string='Import only chosen lines',
        help="If enabled, only rows with 'Yes' in the Import column of the "
             "file will be imported.",
    )
    archive_other_products = fields.Boolean(
        string='Archive other products of this vendor',
        help="Archive any existing Vendor Product records for this vendor "
             "whose code does not appear anywhere in the imported file.",
    )
    archive_previous_stocks = fields.Boolean(
        string='Archive previous stocks of this vendor',
        help="Archive any existing Vendor Stock lines for this vendor that "
             "are NOT present in the imported file, so stock levels exactly "
             "mirror the file.",
    )

    help_html = fields.Html(
        string='Help',
        compute='_compute_help_html',
        sanitize=False,
        help="Maintained in Purchase > Settings > Vendor Product Management.",
    )

    @api.depends_context('lang')
    @api.depends()
    def _compute_help_html(self):
        # No field dependency: the help text comes from the module's
        # configuration (ir.config_parameter), not from any field on this
        # wizard, so the dependency list is intentionally empty. The field
        # is not stored, so it is (re)computed on every read anyway; the
        # decorator above only makes that "no field dependency" explicit.
        help_html = self.env['vendor.import.settings'].get_help_html('stock')
        for wizard in self:
            wizard.help_html = help_html

    def action_download_template(self):
        self.ensure_one()
        url = self.env['vendor.import.settings'].get_template_url('stock')
        if not url:
            raise UserError(
                "No import template is configured. Pick one in "
                "Purchase > Settings > Vendor Product Management."
            )
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    # ------------------------------------------------------------------
    # Import - orchestration
    #
    # The import is split into small steps (read, validate, resolve,
    # write) and every ORM call is batched OUTSIDE the row loops:
    # one search each for the vendor's products, locations, existing
    # stock lines and the UoMs used in the file, one create() for the
    # missing locations, one create() for all new stock lines, and
    # updates grouped by identical values.
    # ------------------------------------------------------------------

    def action_import(self):
        self.ensure_one()
        stats = self._run_import()
        return self._build_result(**stats)

    def _run_import(self):
        """Run the import and return the counters as a plain dict.

        Split out of :meth:`action_import` so the portal controller can
        reuse the exact same parsing and matching rules without going
        through a backend window action.
        """
        self.ensure_one()
        self = self.with_context(skip_catalog_notify=True)
        rows = self._load_rows()
        parsed, errors, skipped = self._parse_rows(rows)
        matched, touched_products = self._resolve_products(parsed, errors)
        location_by_name = self._resolve_locations(matched)
        uom_by_name = self._resolve_uoms(matched)
        pending = self._prepare_pending(matched, location_by_name, uom_by_name, errors)
        created, updated, touched_stock = self._apply_pending(pending)
        archived_products = self._archive_other_products(touched_products)
        archived_stocks = self._archive_previous_stocks(touched_stock)
        return {
            'created': created,
            'updated': updated,
            'archived_products': archived_products,
            'archived_stocks': archived_stocks,
            'skipped': skipped,
            'errors': errors,
        }

    def _load_rows(self):
        """Validate the upload and return the data rows of the sheet."""
        if load_workbook is None:
            raise UserError("openpyxl is required to import Excel files.")
        if not self.import_file:
            raise UserError("Please upload a file to import.")
        try:
            wb = load_workbook(
                filename=io.BytesIO(self.import_file.content),
                data_only=True,
            )
            sheet = wb.active
        except Exception as exc:
            raise UserError("Could not read the uploaded file: %s" % exc)
        return list(sheet.iter_rows(min_row=2, values_only=True))

    def _parse_rows(self, rows):
        """Pure validation pass - no ORM calls in this loop."""
        parsed, errors = [], []
        skipped = 0
        for idx, row in enumerate(rows, start=2):
            if row is None or all(cell in (None, '') for cell in row):
                continue
            line, error, chosen = self._parse_row(idx, row)
            if not chosen:
                skipped += 1
            elif error:
                errors.append(error)
            else:
                parsed.append(line)
        return parsed, errors, skipped

    def _is_row_chosen(self, import_flag):
        """Row selection: only relevant when the option is enabled."""
        if not self.import_only_chosen_lines:
            return True
        flag = str(import_flag).strip().lower() if import_flag is not None else ''
        return flag in TRUE_VALUES

    def _parse_row(self, idx, row):
        """Validate one raw sheet row. Returns (line, error, chosen)."""
        row = list(row) + [None] * (len(TEMPLATE_HEADERS) - len(row))
        import_flag, vendor_code, location_name, quantity, uom_name, note = row[:6]
        if not self._is_row_chosen(import_flag):
            return None, None, False
        vendor_code = str(vendor_code).strip() if vendor_code else ''
        location_name = str(location_name).strip() if location_name else ''
        if not vendor_code:
            return None, "Row %s: Vendor Product Code is required, line skipped." % idx, True
        if not location_name:
            return None, "Row %s: Vendor Location is required, line skipped." % idx, True
        if quantity in (None, ''):
            return None, "Row %s: Quantity is required, line skipped." % idx, True
        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            return None, "Row %s: '%s' is not a valid quantity, line skipped." % (idx, quantity), True
        return {
            'idx': idx,
            'vendor_code': vendor_code,
            'location_name': location_name,
            'quantity': quantity,
            'uom_name': str(uom_name).strip() if uom_name else '',
            'note': note,
        }, None, True

    def _resolve_products(self, parsed, errors):
        """One query for the vendor's catalog; keep only rows whose
        vendor product code exists, like the per-row lookup did."""
        product_by_code = {}
        for rec in self.env['vendor.product'].search([('vendor_id', '=', self.vendor_id.id)]):
            if rec.vendor_code:
                product_by_code.setdefault(rec.vendor_code, rec)
        matched = []
        touched_products = self.env['vendor.product'].browse()
        for line in parsed:
            vendor_product = product_by_code.get(line['vendor_code'])
            if not vendor_product:
                errors.append(
                    "Row %s: no Vendor Product with code '%s' for this vendor. "
                    "Import that product first, line skipped." % (line['idx'], line['vendor_code'])
                )
                continue
            line['vendor_product'] = vendor_product
            matched.append(line)
            touched_products |= vendor_product
        return matched, touched_products

    def _resolve_locations(self, matched):
        """One query for the vendor's locations plus one create() for
        every location name in the file that does not exist yet."""
        location_by_name = {}
        for loc in self.env['vendor.location'].search([('vendor_id', '=', self.vendor_id.id)]):
            location_by_name.setdefault(loc.name, loc)
        missing = []
        seen = set()
        for line in matched:
            name = line['location_name']
            if name not in location_by_name and name not in seen:
                seen.add(name)
                missing.append({'vendor_id': self.vendor_id.id, 'name': name})
        if missing:
            for loc in self.env['vendor.location'].create(missing):
                location_by_name[loc.name] = loc
        return location_by_name

    def _resolve_uoms(self, matched):
        """One query for every UoM name used in the file."""
        names = list({line['uom_name'] for line in matched if line['uom_name']})
        uom_by_name = {}
        if names:
            for uom in self.env['uom.uom'].search([('name', 'in', names)]):
                uom_by_name.setdefault(uom.name, uom)
        return uom_by_name

    def _get_fallback_uom(self):
        """Same fallback the per-row code used, resolved once."""
        if not hasattr(self, '_fallback_uom_cache'):
            self._fallback_uom_cache = self.env['uom.uom'].search([], limit=1)
        return self._fallback_uom_cache

    def _prepare_pending(self, matched, location_by_name, uom_by_name, errors):
        """Turn matched rows into pending entries keyed by
        (vendor product, location), so several rows for the same
        combination merge exactly as sequential imports did."""
        now = fields.Datetime.now()
        pending = {}
        for line in matched:
            vendor_product = line['vendor_product']
            location = location_by_name[line['location_name']]

            uom = False
            if line['uom_name']:
                uom = uom_by_name.get(line['uom_name'], False)
                if not uom:
                    errors.append(
                        "Row %s: no Unit of Measure named '%s' found, "
                        "using product's UoM instead." % (line['idx'], line['uom_name'])
                    )
            if not uom:
                uom = vendor_product.product_id.uom_id or self._get_fallback_uom()

            values = {
                'vendor_product_id': vendor_product.id,
                'location_id': location.id,
                'quantity': line['quantity'],
                'uom_id': uom.id if uom else False,
                'last_updated': now,
                'active': True,
            }
            if line['note']:
                values['note'] = str(line['note']).strip()

            key = (vendor_product.id, location.id)
            entry = pending.get(key)
            if entry is None:
                entry = pending[key] = {'vals': {}, 'hits': 0}
            entry['hits'] += 1
            entry['vals'].update(values)
        return pending

    def _apply_pending(self, pending):
        """Batched writes: one search for the existing stock lines, one
        create() for all new lines, updates grouped by identical values."""
        VendorStock = self.env['vendor.stock']
        existing_by_key = {}
        records = VendorStock.with_context(active_test=False).search(
            [('vendor_id', '=', self.vendor_id.id)]
        )
        for rec in records:
            existing_by_key.setdefault((rec.vendor_product_id.id, rec.location_id.id), rec)

        to_create, updates = [], []
        created = updated = 0
        for key, entry in pending.items():
            existing = existing_by_key.get(key)
            if existing:
                updates.append((existing, entry['vals']))
                updated += entry['hits']
            else:
                to_create.append(entry['vals'])
                created += 1
                updated += entry['hits'] - 1
        new_records = VendorStock.create(to_create) if to_create else VendorStock.browse()
        touched = self._write_grouped(updates) | new_records
        return created, updated, touched

    def _write_grouped(self, updates):
        """Apply the pending updates with the minimum number of queries.

        Values shared by every updated record (and not under chatter
        tracking, so message grouping is unchanged) are hoisted into a
        single write() over the whole recordset. Only the genuinely
        record-specific remainder is then applied per record - each of
        those records receives different data, so that part cannot be
        merged into fewer queries by any batching strategy."""
        touched = self.env['vendor.stock'].browse()
        if not updates:
            return touched
        for record, _vals in updates:
            touched |= record
        common = self._extract_common_vals(updates)
        if common:
            touched.write(common)
        for record, vals in updates:
            self._write_record_specific(
                record, {k: v for k, v in vals.items() if k not in common}
            )
        return touched

    def _extract_common_vals(self, updates):
        """Return the key/value pairs present with an identical value in
        EVERY update, restricted to untracked fields so the chatter
        output stays exactly as before."""
        fields_def = self.env['vendor.stock']._fields
        missing = object()
        common = {}
        for key, value in updates[0][1].items():
            field = fields_def.get(key)
            if field is not None and getattr(field, 'tracking', False):
                continue
            if all(vals.get(key, missing) == value for _record, vals in updates):
                common[key] = value
        return common

    def _write_record_specific(self, record, vals):
        """Write one record's own values. Each record here receives
        different data, so these writes are irreducibly per-record."""
        if vals:
            record.write(vals)

    def _archive_other_products(self, touched_products):
        """Archive the vendor's products whose code did not appear in the
        file - i.e. every active record this run never referenced."""
        if not self.archive_other_products:
            return 0
        to_archive = self.env['vendor.product'].search([
            ('vendor_id', '=', self.vendor_id.id),
            ('id', 'not in', touched_products.ids or [0]),
        ])
        if to_archive:
            to_archive.write({'active': False})
        return len(to_archive)

    def _archive_previous_stocks(self, touched_stock):
        """Archive the vendor's stock lines that were NOT in the file."""
        if not self.archive_previous_stocks:
            return 0
        domain = [('vendor_id', '=', self.vendor_id.id)]
        if touched_stock:
            domain.append(('id', 'not in', touched_stock.ids))
        to_archive = self.env['vendor.stock'].search(domain)
        if to_archive:
            to_archive.write({'active': False})
        return len(to_archive)

    def _build_result(self, created, updated, archived_products, archived_stocks, skipped, errors):
        summary_lines = [
            "<ul>",
            "<li><b>%s</b> vendor stock line(s) created</li>" % created,
            "<li><b>%s</b> vendor stock line(s) updated</li>" % updated,
        ]
        if self.archive_other_products:
            summary_lines.append("<li><b>%s</b> vendor product(s) archived</li>" % archived_products)
        if self.archive_previous_stocks:
            summary_lines.append("<li><b>%s</b> vendor stock line(s) archived</li>" % archived_stocks)
        if self.import_only_chosen_lines:
            summary_lines.append("<li><b>%s</b> row(s) skipped (not chosen)</li>" % skipped)
        summary_lines.append("<li><b>%s</b> error(s)</li>" % len(errors))
        summary_lines.append("</ul>")

        result = self.env['vendor.import.result'].create({
            'name': 'Import Vendor Stocks - Results',
            'created_count': created,
            'updated_count': updated,
            'archived_count': archived_products + archived_stocks,
            'skipped_count': skipped,
            'error_count': len(errors),
            'summary': ''.join(summary_lines),
            'error_details': '\n'.join(errors) if errors else False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.import.result',
            'res_id': result.id,
            'view_mode': 'form',
            'target': 'new',
        }


def build_vendor_stock_template():
    """Build the downloadable Vendor Stocks import template as xlsx bytes."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'Vendor Stock'
    ws.append(TEMPLATE_HEADERS)
    ws.append(['Yes', 'SUP-001', 'Main Warehouse', 100, 'Units', ''])
    for col, width in zip('ABCDEF', [16, 20, 24, 12, 14, 30]):
        ws.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
