# -*- coding: utf-8 -*-
"""Structural extensions of ``edm.document`` for heavy repositories.

This file *extends* the existing model (``_inherit``) instead of editing it, so
every field, action and view already shipped keeps working untouched.

What it adds
------------
* ``sequence``   - explicit, persisted ordering (drag & drop handle in list view)
* ``group_id``   - relational grouping, no file duplication
* ``file_size``  - metadata only, never reads the binary payload
* database indexes on the columns the DMS filters / groups on
* a reusable access-checking helper used by every bulk action
* batch helpers (``action_bulk_*``) that write once instead of once per record
"""

import base64
import io
import mimetypes
import re
import zipfile

from odoo import models, fields, api, _
from odoo.exceptions import UserError


def b64_decoded_size(data):
    """Return the decoded byte size of base64 ``data`` without decoding it."""
    if not data:
        return 0
    if isinstance(data, bytes):
        data = data.decode('ascii', errors='ignore')
    length = len(data)
    if not length:
        return 0
    padding = data[-2:].count('=')
    return max((length * 3) // 4 - padding, 0)


def human_size(num_bytes):
    """Human readable file size ('5.2 MB')."""
    if not num_bytes:
        return '0 B'
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == 'B':
                return '%d %s' % (int(size), unit)
            return '%.1f %s' % (size, unit)
        size /= 1024.0
    return '%.1f TB' % size


class EdmDocument(models.Model):
    _inherit = 'edm.document'
    _order = 'sequence asc, id desc'

    # ------------------------------------------------------------------
    # NEW STRUCTURAL FIELDS
    # ------------------------------------------------------------------
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        index=True,
        help="Position of the document inside its folder / group. "
             "Use the drag handle in the list view or the bulk Reorder action.",
    )

    group_id = fields.Many2one(
        'edm.document.group',
        string='Group',
        index=True,
        ondelete='set null',
        help="Logical group this document belongs to. Grouping uses a database "
             "relation only - the file itself is never duplicated.",
    )

    file_size = fields.Integer(
        string='Size (bytes)',
        readonly=True,
        default=0,
        help="Size of the stored file. Kept as plain metadata so listing "
             "documents never loads the binary content.",
    )

    file_size_display = fields.Char(
        string='Size',
        compute='_compute_file_size_display',
    )

    @api.depends('file_size')
    def _compute_file_size_display(self):
        for record in self:
            record.file_size_display = human_size(record.file_size)

    # ------------------------------------------------------------------
    # INDEXES ON EXISTING COLUMNS (heavy environments)
    # ------------------------------------------------------------------
    # --- Metadata required by section 8.4 (Edit Metadata) and section 10
    #     (Search and Filtering). All plain columns: adding them costs one
    #     ALTER TABLE and changes no existing behaviour.
    description = fields.Text(
        string="Description",
        help="Free-form notes about this document.",
    )

    category_id = fields.Many2one(
        'edm.document.category',
        string="Category",
        index=True,
        ondelete='set null',
    )

    project_reference = fields.Char(
        string="Project / Reference",
        index=True,
        help="External project code or reference this document belongs to.",
    )

    reference = fields.Char(
        string="Internal Reference",
        copy=False,
        readonly=True,
        index=True,
        help="Generated automatically when the document is created.",
    )

    mimetype = fields.Char(
        string="Mime Type",
        compute='_compute_mimetype',
        store=True,
        help="Resolved from the file name - the binary is never read.",
    )

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        index=True,
        default=lambda self: self.env.company,
    )

    @api.depends('file_name', 'file_extension')
    def _compute_mimetype(self):
        """Resolve the mime type from the file name only."""
        for record in self:
            guessed = None
            if record.file_name:
                guessed = mimetypes.guess_type(record.file_name)[0]
            if not guessed and record.file_extension:
                guessed = mimetypes.guess_type(
                    'x.%s' % record.file_extension)[0]
            record.mimetype = guessed or False

    name = fields.Char(index='trigram')
    workspace_id = fields.Many2one(index=True)
    folder_id = fields.Many2one(index=True)
    owner_id = fields.Many2one(index=True)
    is_trashed = fields.Boolean(index=True)
    is_favorite = fields.Boolean(index=True)
    file_extension = fields.Char(index=True)
    state = fields.Selection(index=True)

    # ------------------------------------------------------------------
    # SIZE BOOKKEEPING (no binary reads, no stored-compute recompute storm)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'file' in vals:
                vals['file_size'] = b64_decoded_size(vals.get('file'))
            if not vals.get('reference'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'edm.document') or '/'
            # A category may carry a default validity period.
            if vals.get('category_id') and not vals.get('expiry_date'):
                category = self.env['edm.document.category'].browse(
                    vals['category_id'])
                if category.default_expiry_days:
                    vals['expiry_date'] = fields.Date.add(
                        fields.Date.today(),
                        days=category.default_expiry_days)
        return super().create(vals_list)

    def write(self, vals):
        if 'file' in vals:
            vals = dict(vals, file_size=b64_decoded_size(vals.get('file')))
        return super().write(vals)

    # ------------------------------------------------------------------
    # ACCESS HELPERS FOR BULK OPERATIONS
    # ------------------------------------------------------------------
    def _split_by_access(self, operation):
        """Return ``(allowed, denied)`` recordsets for ``operation``.

        Uses the standard Odoo access-rights / record-rules machinery, so bulk
        actions can never bypass ``ir.model.access`` or ``ir.rule``.
        """
        if hasattr(self, '_filtered_access'):
            allowed = self._filtered_access(operation)
        else:  # pragma: no cover - defensive fallback for older ORMs
            allowed = self.browse()
            for record in self:
                try:
                    record.check_access(operation)
                except Exception:
                    continue
                allowed |= record
        return allowed, self - allowed

    def _check_bulk_access(self, operation, block_locked=False):
        """Validate a whole selection before touching anything.

        Raises a clear :class:`UserError` listing the offending documents
        instead of silently applying the operation to a subset.
        """
        if not self:
            raise UserError(_("No document selected."))

        allowed, denied = self._split_by_access(operation)
        if denied:
            raise UserError(_(
                "You are not allowed to %(operation)s %(count)s of the "
                "%(total)s selected documents:\n\n%(names)s\n\n"
                "Nothing has been changed. Please narrow your selection.",
                operation=operation,
                count=len(denied),
                total=len(self),
                names='\n'.join('- %s' % (doc.display_name or _('Unnamed'))
                                for doc in denied[:10])
                + ('\n- ...' if len(denied) > 10 else ''),
            ))

        if block_locked:
            locked = self.filtered('is_locked')
            if locked:
                raise UserError(_(
                    "%(count)s selected document(s) are locked:\n\n%(names)s\n\n"
                    "Unlock them first.",
                    count=len(locked),
                    names='\n'.join('- %s' % doc.display_name
                                    for doc in locked[:10]),
                ))
        return self

    # ------------------------------------------------------------------
    # BATCH PRIMITIVES
    # ------------------------------------------------------------------
    # Rows per UPDATE statement when renumbering a large selection.
    SEQUENCE_BATCH_SIZE = 1000

    def _bulk_set_sequences(self, sequences):
        """Assign ``{record_id: sequence}`` in a single SQL statement.

        ``sequence`` is a plain integer column with no compute dependency and
        no tracking, so a set-based UPDATE is safe and avoids one round trip
        per document on large selections.
        """
        sequences = {rid: int(seq) for rid, seq in sequences.items() if rid}
        if not sequences:
            return
        self.env.flush_all()
        items = list(sequences.items())
        for start in range(0, len(items), self.SEQUENCE_BATCH_SIZE):
            chunk = items[start:start + self.SEQUENCE_BATCH_SIZE]
            self.env.cr.execute(
                """
                UPDATE edm_document AS d
                   SET sequence = v.sequence
                  FROM (VALUES %s) AS v(id, sequence)
                 WHERE d.id = v.id
                """ % ','.join(['(%s::int, %s::int)'] * len(chunk)),
                [value for item in chunk for value in item],
            )
        self.invalidate_recordset(['sequence'])

    # ------------------------------------------------------------------
    # POST-UPLOAD MANAGEMENT
    # ------------------------------------------------------------------
    def action_open_share_wizard(self):
        """Open the share wizard, which grants real per-user access.

        The wizard and its form view already shipped but had no action and no
        button, so it was unreachable from the interface.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Share Document"),
            'res_model': 'edm.document.share.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_document_id': self.id},
        }

    def action_replace_file(self):
        """Open the version wizard to replace the physical file in place.

        The current file is archived as a new ``edm.document.version`` record,
        so replacing a file never loses the previous revision.
        """
        self.ensure_one()
        self._check_bulk_access('write', block_locked=True)
        return {
            'type': 'ir.actions.act_window',
            'name': _("Replace File"),
            'res_model': 'edm.document.version.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_document_id': self.id},
        }

    def action_edit_metadata(self):
        """Open the document form so every metadata field can be edited."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name,
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    # Single-record entry points for the document action menu. They reuse the
    # exact same wizard as the multi-selection bulk actions.
    def action_move_dialog(self):
        return self.with_context(bulk_action_type='move').action_open_bulk_wizard()

    def action_group_dialog(self):
        return self.with_context(bulk_action_type='group').action_open_bulk_wizard()

    def action_tags_dialog(self):
        return self.with_context(bulk_action_type='tags').action_open_bulk_wizard()

    def action_open_bulk_wizard(self):
        """Generic entry point used by the bulk action bindings."""
        action_type = self.env.context.get('bulk_action_type', 'move')
        return {
            'type': 'ir.actions.act_window',
            'name': _("Bulk Actions"),
            'res_model': 'edm.document.bulk.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_action_type': action_type,
                'active_ids': self.ids,
                'active_model': self._name,
            },
        }

    # ------------------------------------------------------------------
    # BULK DOWNLOAD
    # ------------------------------------------------------------------
    # The archive is streamed through a temporary file on disk, so only one
    # document is ever decoded in memory at a time. The guards below keep a
    # careless selection from filling the disk or producing a download URL
    # longer than the HTTP request line allows.
    MAX_ZIP_BYTES = 1024 * 1024 * 1024
    MAX_ZIP_DOCUMENTS = 300

    def action_bulk_download(self):
        """Download the selection: one file directly, several as a ZIP."""
        documents = self._check_bulk_access('read')
        downloadable = documents.filtered(
            lambda doc: doc.document_type != 'url')
        if not downloadable:
            raise UserError(_("The selected documents contain no file to download."))

        if len(downloadable) == 1:
            return downloadable.action_download_document()

        if len(downloadable) > self.MAX_ZIP_DOCUMENTS:
            raise UserError(_(
                "You selected %(count)s documents. Bulk download is limited to "
                "%(limit)s documents at a time - please download them in "
                "smaller batches.",
                count=len(downloadable), limit=self.MAX_ZIP_DOCUMENTS,
            ))

        total = sum(downloadable.mapped('file_size'))
        if total > self.MAX_ZIP_BYTES:
            raise UserError(_(
                "The selection is too large to zip (%(size)s). "
                "Please download it in smaller batches.",
                size=human_size(total),
            ))

        return {
            'type': 'ir.actions.act_url',
            'url': '/edm/documents/download_zip?ids=%s' % ','.join(
                str(doc_id) for doc_id in downloadable.ids),
            'target': 'self',
        }

    ZIP_FILE_NAME = 'documents.zip'

    def _write_zip(self, fileobj):
        """Write a ZIP archive of ``self`` into ``fileobj``.

        Documents are decoded and appended one at a time and the record cache
        is dropped after each of them, so peak memory stays at the size of the
        single largest document instead of the whole selection.
        """
        used_names = {}
        with zipfile.ZipFile(fileobj, 'w', zipfile.ZIP_DEFLATED) as archive:
            for document in self:
                payload = document.file
                if not payload:
                    continue
                filename = document.file_name or document.name or 'document'
                filename = re.sub(r'[\\/:*?"<>|]+', '_', filename)
                count = used_names.get(filename, 0)
                used_names[filename] = count + 1
                if count:
                    stem, dot, extension = filename.rpartition('.')
                    filename = ('%s (%s)%s%s' % (stem, count, dot, extension)
                                if dot else '%s (%s)' % (filename, count))
                archive.writestr(filename, base64.b64decode(payload))
                document.invalidate_recordset(['file'])
        return self.ZIP_FILE_NAME

    def _build_zip(self):
        """Return ``(filename, bytes)`` for a ZIP archive of ``self``.

        In-memory variant, kept for callers that need the raw bytes. The HTTP
        download route streams from disk instead - see ``_write_zip``.
        """
        buffer = io.BytesIO()
        name = self._write_zip(buffer)
        return name, buffer.getvalue()
