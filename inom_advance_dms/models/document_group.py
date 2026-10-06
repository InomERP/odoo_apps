# -*- coding: utf-8 -*-
"""Logical document groups.

A group is a pure *relational* container: documents point at a group through
``edm.document.group_id``. No file / attachment is ever duplicated, so grouping
thousands of documents costs one integer column update per document.
"""

from odoo import models, fields, api


class EdmDocumentGroup(models.Model):
    _name = 'edm.document.group'
    _description = 'Document Group'
    _order = 'sequence, name'

    name = fields.Char(string='Group Name', required=True, index='trigram')
    description = fields.Text(string='Description')
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)

    workspace_id = fields.Many2one('edm.workspace', string='Workspace', index=True)
    folder_id = fields.Many2one('edm.folder', string='Folder', index=True)

    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        index=True,
    )

    document_ids = fields.One2many(
        'edm.document', 'group_id', string='Documents')

    document_count = fields.Integer(
        string='Document Count', compute='_compute_document_count')

    @api.depends('document_ids')
    def _compute_document_count(self):
        """One aggregated query instead of reading every related document."""
        counts = {}
        if self.ids:
            grouped = self.env['edm.document']._read_group(
                [('group_id', 'in', self.ids)],
                groupby=['group_id'],
                aggregates=['__count'],
            )
            counts = {group.id: count for group, count in grouped}
        for record in self:
            record.document_count = counts.get(record.id, 0)

    def action_open_documents(self):
        """Open the documents belonging to this group."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'edm.document',
            'view_mode': 'list,kanban,form',
            'domain': [('group_id', '=', self.id), ('is_trashed', '=', False)],
            'context': {
                'default_group_id': self.id,
                'default_workspace_id': self.workspace_id.id,
                'default_folder_id': self.folder_id.id,
            },
        }
