# -*- coding: utf-8 -*-
"""Reusable bulk-action framework for ``edm.document``.

One wizard drives every bulk operation. Adding a new bulk action later only
requires two things:

1. add a value to the ``action_type`` selection;
2. implement ``_apply_<value>(documents)``.

The selection mechanism, the access checks, the notification and the view
refresh are shared and never have to be rewritten.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EdmDocumentBulkWizard(models.TransientModel):
    _name = 'edm.document.bulk.wizard'
    _description = 'Document Bulk Actions'

    # Which ORM operation each bulk action needs to be allowed to perform.
    ACTION_OPERATION = {
        'move': 'write',
        'group': 'write',
        'reorder': 'write',
        'tags': 'write',
        'category': 'write',
        'state': 'write',
        'archive': 'write',
        'trash': 'write',
        'download': 'read',
        'delete': 'unlink',
    }

    # Actions that must refuse to touch locked documents.
    LOCK_SENSITIVE = ('move', 'reorder', 'category', 'state', 'archive',
                      'trash', 'delete')

    action_type = fields.Selection(
        selection=[
            ('move', 'Move to Folder'),
            ('group', 'Group Documents'),
            ('reorder', 'Reorder'),
            ('tags', 'Change Tags'),
            ('category', 'Change Category'),
            ('state', 'Change Status'),
            ('archive', 'Archive / Restore'),
            ('download', 'Download'),
            ('trash', 'Send to Recycle Bin'),
            ('delete', 'Delete Permanently'),
        ],
        string='Action',
        required=True,
        default='move',
    )

    category_id = fields.Many2one(
        'edm.document.category',
        string='Category',
        help="Category applied to every selected document.",
    )

    clear_category = fields.Boolean(
        string='Clear Category',
        help="Remove the category instead of setting a new one.",
    )

    document_ids = fields.Many2many(
        'edm.document',
        string='Selected Documents',
        default=lambda self: [(6, 0, self.env.context.get('active_ids', []))],
    )

    document_count = fields.Integer(
        string='Selected', compute='_compute_document_count')

    # --- Move -------------------------------------------------------------
    workspace_id = fields.Many2one('edm.workspace', string='Destination Workspace')
    folder_id = fields.Many2one('edm.folder', string='Destination Folder')
    keep_workspace = fields.Boolean(
        string='Keep Current Workspace', default=True,
        help="Leave the workspace untouched and only change the folder.")

    # --- Group ------------------------------------------------------------
    group_mode = fields.Selection(
        [('existing', 'Use Existing Group'), ('new', 'Create New Group')],
        string='Group Mode', default='new')
    group_id = fields.Many2one('edm.document.group', string='Group')
    new_group_name = fields.Char(string='New Group Name')
    group_description = fields.Text(string='Group Description')

    # --- Reorder ----------------------------------------------------------
    sequence_start = fields.Integer(string='Start Position', default=10)
    sequence_step = fields.Integer(string='Step', default=10)

    # --- Tags -------------------------------------------------------------
    tag_mode = fields.Selection(
        [('add', 'Add Tags'), ('remove', 'Remove Tags'), ('replace', 'Replace Tags')],
        string='Tag Mode', default='add')
    tag_ids = fields.Many2many('edm.tag', string='Tags')

    # --- Status -----------------------------------------------------------
    state = fields.Selection(
        [('draft', 'Draft'), ('waiting', 'Waiting'),
         ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='New Status', default='draft')

    # --- Archive ----------------------------------------------------------
    archive_mode = fields.Selection(
        [('archive', 'Archive'), ('restore', 'Restore')],
        string='Archive Mode', default='archive')

    @api.depends('document_ids')
    def _compute_document_count(self):
        for wizard in self:
            wizard.document_count = len(wizard.document_ids)

    # ------------------------------------------------------------------
    # DISPATCHER
    # ------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        # ``active_test=False`` so archived documents stay in the selection
        # (needed for the Restore action).
        documents = self.with_context(active_test=False).document_ids
        if not documents:
            raise UserError(_("No document selected."))

        operation = self.ACTION_OPERATION.get(self.action_type, 'write')
        documents._check_bulk_access(
            operation,
            block_locked=self.action_type in self.LOCK_SENSITIVE,
        )

        handler = getattr(self, '_apply_%s' % self.action_type, None)
        if handler is None:
            raise UserError(_("Unknown bulk action: %s", self.action_type))

        result = handler(documents)
        if isinstance(result, dict):
            # A handler may return its own action (e.g. the download URL).
            return result
        return self._notify(result or _("Operation completed."))

    def _notify(self, message, title=None, kind='success'):
        """Show feedback and refresh the calling view."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title or _("Bulk Action"),
                'message': message,
                'type': kind,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    # ------------------------------------------------------------------
    # HANDLERS - one batched write per action
    # ------------------------------------------------------------------
    def _apply_move(self, documents):
        if not self.folder_id and not self.workspace_id:
            raise UserError(_("Select a destination folder or workspace."))

        values = {}
        if self.folder_id:
            values['folder_id'] = self.folder_id.id
        if self.workspace_id and not self.keep_workspace:
            values['workspace_id'] = self.workspace_id.id
        elif self.folder_id and self.folder_id.workspace_id and not self.keep_workspace:
            values['workspace_id'] = self.folder_id.workspace_id.id

        documents.write(values)  # single batched write
        return _("%(count)s document(s) moved to %(target)s.",
                 count=len(documents),
                 target=self.folder_id.complete_name
                 or self.workspace_id.display_name)

    def _apply_group(self, documents):
        if self.group_mode == 'new':
            name = (self.new_group_name or '').strip()
            if not name:
                raise UserError(_("Please enter a name for the new group."))
            group = self.env['edm.document.group'].create({
                'name': name,
                'description': self.group_description,
                'workspace_id': self.workspace_id.id or documents[:1].workspace_id.id,
                'folder_id': self.folder_id.id or documents[:1].folder_id.id,
            })
        else:
            group = self.group_id
            if not group:
                raise UserError(_("Please select an existing group."))

        # Relational assignment only - no file is copied or duplicated.
        documents.write({'group_id': group.id})
        return _("%(count)s document(s) added to group \"%(group)s\".",
                 count=len(documents), group=group.name)

    def _apply_reorder(self, documents):
        step = self.sequence_step or 1
        start = self.sequence_start or 0
        ordered = documents.sorted(lambda doc: (doc.sequence, -doc.id))
        documents._bulk_set_sequences({
            document.id: start + index * step
            for index, document in enumerate(ordered)
        })
        return _("%(count)s document(s) reordered from position %(start)s.",
                 count=len(documents), start=start)

    def _apply_tags(self, documents):
        if not self.tag_ids and self.tag_mode != 'replace':
            raise UserError(_("Please select at least one tag."))
        if self.tag_mode == 'add':
            command = [(4, tag.id) for tag in self.tag_ids]
        elif self.tag_mode == 'remove':
            command = [(3, tag.id) for tag in self.tag_ids]
        else:
            command = [(6, 0, self.tag_ids.ids)]
        documents.write({'tag_ids': command})
        return _("Tags updated on %(count)s document(s).", count=len(documents))

    def _apply_category(self, documents):
        """Set or clear the category on the whole selection in one write."""
        if not self.category_id and not self.clear_category:
            raise UserError(_("Please choose a category, or tick Clear Category."))

        target = self.category_id.id if not self.clear_category else False
        # Skip records that already carry the target value.
        to_write = documents.filtered(lambda d: d.category_id.id != target)
        if to_write:
            to_write.write({'category_id': target})

        if self.clear_category:
            return _("Category cleared on %(count)s document(s).",
                     count=len(to_write))
        return _("%(count)s document(s) moved to category \"%(category)s\".",
                 count=len(to_write), category=self.category_id.name)

    def _apply_state(self, documents):
        documents.write({'state': self.state})
        return _("Status set to %(state)s on %(count)s document(s).",
                 state=dict(self._fields['state'].selection)[self.state],
                 count=len(documents))

    def _apply_archive(self, documents):
        # Archiving clears ``active``; restoring sets it back.
        documents.write({'active': self.archive_mode != 'archive'})
        if self.archive_mode == 'archive':
            return _("%(count)s document(s) archived.", count=len(documents))
        return _("%(count)s document(s) restored.", count=len(documents))

    def _apply_trash(self, documents):
        documents.write({
            'is_trashed': True,
            'trashed_date': fields.Datetime.now(),
        })
        return _("%(count)s document(s) moved to the Recycle Bin.",
                 count=len(documents))

    def _apply_delete(self, documents):
        count = len(documents)
        documents.unlink()
        return _("%(count)s document(s) permanently deleted.", count=count)

    def _apply_download(self, documents):
        return documents.action_bulk_download()
