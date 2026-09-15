# -*- coding: utf-8 -*-
"""Document category.

A category describes *what a document is* (Contract, Drawing, Certificate).
It is deliberately separate from ``edm.folder`` (where a document lives) and
``edm.document.group`` (an ad-hoc bundle of documents), so the three can be
combined freely.
"""

from odoo import models, fields, api


class EdmDocumentCategory(models.Model):
    _name = 'edm.document.category'
    _description = 'Document Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category', required=True, index=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(string='Code')
    description = fields.Text()
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)

    default_expiry_days = fields.Integer(
        string='Default Validity (days)',
        help="When set, a document created in this category automatically "
             "gets an expiry date this many days after creation.")

    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.company)

    document_count = fields.Integer(
        string='Documents', compute='_compute_document_count')

    def _compute_document_count(self):
        counts = {}
        if self.ids:
            rows = self.env['edm.document']._read_group(
                [('category_id', 'in', self.ids), ('is_trashed', '=', False)],
                groupby=['category_id'],
                aggregates=['__count'],
            )
            counts = {category.id: count for category, count in rows}
        for record in self:
            record.document_count = counts.get(record.id, 0)

    def action_open_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'edm.document',
            'view_mode': 'list,kanban,form',
            'domain': [('category_id', '=', self.id),
                       ('is_trashed', '=', False)],
            'context': {'default_category_id': self.id},
        }
