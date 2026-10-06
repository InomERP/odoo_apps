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
    'Vendor Product Name',
    'Internal Product Reference',
    'Vendor Price',
    'Notes',
]

TRUE_VALUES = {'yes', 'y', 'true', '1', 'x'}


class VendorProductImportWizard(models.TransientModel):
    _name = 'vendor.product.import.wizard'
    _description = 'Import Vendor Products'

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
        help="Upload a filled-in copy of the predefined Vendor Products "
             "template (see the Help tab).",
    )
    import_filename = fields.Char(string='Filename')

    import_only_chosen_lines = fields.Boolean(
        string='Import only chosen lines',
        help="If enabled, only rows with 'Yes' in the Import column of the "
             "file will be imported. Useful for large supplier files where "
             "you only want part of the sheet.",
    )
    archive_other_products = fields.Boolean(
        string='Archive other products of this vendor',
        help="Archive any existing Vendor Product records for this vendor "
             "that are NOT present in the imported file, so the catalog "
             "exactly mirrors the file.",
    )
    mark_previous_prices_outdated = fields.Boolean(
        string='Mark previous prices as outdated',
        help="Flag the previous price on every updated line as outdated "
             "before the new price is applied, so you can see at a glance "
             "which prices just changed.",
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
        help_html = self.env['vendor.import.settings'].get_help_html('product')
        for wizard in self:
            wizard.help_html = help_html

    def action_download_template(self):
        self.ensure_one()
        url = self.env['vendor.import.settings'].get_template_url('product')
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
    # one search for internal products, one search for the vendor's
    # existing catalog, one create() for all new rows, and updates
    # grouped by identical values.
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
        product_by_ref = self._resolve_internal_products(parsed)
        pending = self._prepare_pending(parsed, product_by_ref, errors)
        created, updated, touched = self._apply_pending(pending)
        archived = self._archive_other_products(touched)
        return {
            'created': created,
            'updated': updated,
            'archived': archived,
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
        import_flag, vendor_code, vendor_name, internal_ref, price, note = row[:6]
        if not self._is_row_chosen(import_flag):
            return None, None, False
        vendor_code = (str(vendor_code).strip() if vendor_code else '')
        vendor_name = (str(vendor_name).strip() if vendor_name else '')
        if not vendor_name:
            return None, "Row %s: Vendor Product Name is required, line skipped." % idx, True
        return {
            'idx': idx,
            'vendor_code': vendor_code,
            'vendor_name': vendor_name,
            'internal_ref': str(internal_ref).strip() if internal_ref else '',
            'price': price,
            'note': note,
        }, None, True

    def _resolve_internal_products(self, parsed):
        """One query for every internal reference used in the file."""
        refs = list({line['internal_ref'] for line in parsed if line['internal_ref']})
        product_by_ref = {}
        if refs:
            for product in self.env['product.product'].search([('default_code', 'in', refs)]):
                # keep the first hit per reference, like search(limit=1) did
                product_by_ref.setdefault(product.default_code, product.id)
        return product_by_ref

    def _get_existing_catalog(self):
        """One query for the vendor's whole catalog (archived included)."""
        records = self.env['vendor.product'].with_context(active_test=False).search(
            [('vendor_id', '=', self.vendor_id.id)]
        )
        by_code, by_name = {}, {}
        for rec in records:
            if rec.vendor_code:
                by_code.setdefault(rec.vendor_code, rec)
            by_name.setdefault(rec.vendor_product_name, rec)
        return by_code, by_name

    def _prepare_pending(self, parsed, product_by_ref, errors):
        """Turn validated rows into pending create/update entries.

        Rows are keyed the same way the record lookup works (vendor code
        when present, otherwise vendor product name), so several rows for
        the same vendor product merge exactly as sequential imports did.
        """
        by_code, by_name = self._get_existing_catalog()
        now = fields.Datetime.now()
        pending = {}
        for line in parsed:
            key = ('code', line['vendor_code']) if line['vendor_code'] \
                else ('name', line['vendor_name'])
            entry = pending.get(key)
            if entry is None:
                existing = by_code.get(line['vendor_code']) if line['vendor_code'] \
                    else by_name.get(line['vendor_name'])
                entry = pending[key] = {'existing': existing, 'vals': {}, 'hits': 0}
            entry['hits'] += 1
            self._update_row_values(entry, line, product_by_ref, errors, now)
        return pending

    def _update_row_values(self, entry, line, product_by_ref, errors, now):
        """Merge one validated row into its pending entry's values."""
        values = entry['vals']
        values.update({
            'vendor_id': self.vendor_id.id,
            'vendor_product_name': line['vendor_name'],
            'active': True,
        })
        if line['vendor_code']:
            values['vendor_code'] = line['vendor_code']
        elif not entry['existing']:
            values['vendor_code'] = False
        if line['internal_ref']:
            product_id = product_by_ref.get(line['internal_ref'], False)
            if product_id:
                values['product_id'] = product_id
            else:
                errors.append(
                    "Row %s: no product found with internal reference '%s', "
                    "product left unmatched." % (line['idx'], line['internal_ref'])
                )
        if line['note']:
            values['note'] = str(line['note']).strip()
        self._update_row_price(values, line, errors, now)

    def _update_row_price(self, values, line, errors, now):
        """Apply the row's price to the pending values, if valid."""
        if line['price'] in (None, ''):
            return
        try:
            new_price = float(line['price'])
        except (TypeError, ValueError):
            errors.append("Row %s: '%s' is not a valid price, price left unchanged."
                          % (line['idx'], line['price']))
            return
        values['vendor_price'] = new_price
        values['price_outdated'] = False
        values['price_last_updated'] = now

    def _apply_pending(self, pending):
        """Batched writes: one create() for all new rows, updates grouped
        by identical values, and the 'outdated' flag set in one write."""
        VendorProduct = self.env['vendor.product']
        to_create, updates = [], []
        to_flag = VendorProduct.browse()
        created = updated = 0
        for entry in pending.values():
            existing = entry['existing']
            if existing:
                if (self.mark_previous_prices_outdated
                        and 'vendor_price' in entry['vals']
                        and existing.vendor_price != entry['vals']['vendor_price']):
                    to_flag |= existing
                updates.append((existing, entry['vals']))
                updated += entry['hits']
            else:
                to_create.append(entry['vals'])
                created += 1
                updated += entry['hits'] - 1
        if to_flag:
            to_flag.write({'price_outdated': True})
        new_records = VendorProduct.create(to_create) if to_create else VendorProduct.browse()
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
        touched = self.env['vendor.product'].browse()
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
        fields_def = self.env['vendor.product']._fields
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

    def _archive_other_products(self, touched):
        """Archive the vendor's products that were NOT in the file - i.e.
        every active record not created or updated by this run."""
        if not self.archive_other_products:
            return 0
        to_archive = self.env['vendor.product'].search([
            ('vendor_id', '=', self.vendor_id.id),
            ('id', 'not in', touched.ids or [0]),
        ])
        if to_archive:
            to_archive.write({'active': False})
        return len(to_archive)

    def _build_result(self, created, updated, archived, skipped, errors):
        summary_lines = [
            "<ul>",
            "<li><b>%s</b> vendor product(s) created</li>" % created,
            "<li><b>%s</b> vendor product(s) updated</li>" % updated,
        ]
        if self.archive_other_products:
            summary_lines.append("<li><b>%s</b> vendor product(s) archived</li>" % archived)
        if self.import_only_chosen_lines:
            summary_lines.append("<li><b>%s</b> row(s) skipped (not chosen)</li>" % skipped)
        summary_lines.append("<li><b>%s</b> error(s)</li>" % len(errors))
        summary_lines.append("</ul>")

        result = self.env['vendor.import.result'].create({
            'name': 'Import Vendor Products - Results',
            'created_count': created,
            'updated_count': updated,
            'archived_count': archived,
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


def build_vendor_product_template():
    """Build the downloadable Vendor Products import template as xlsx bytes."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'Vendor Products'
    ws.append(TEMPLATE_HEADERS)
    ws.append(['Yes', 'SUP-001', 'Sample Vendor Product Name', 'INTERNAL-REF-01', 19.90, ''])
    for col, width in zip('ABCDEF', [16, 20, 32, 24, 14, 30]):
        ws.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
