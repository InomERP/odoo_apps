# -*- coding: utf-8 -*-
from odoo import api, models, fields


class VendorImportResult(models.TransientModel):
    _name = 'vendor.import.result'
    _description = 'Vendor Import Result'

    name = fields.Char(string='Import Summary', default='Import Results')
    created_count = fields.Integer(string='Created')
    updated_count = fields.Integer(string='Updated')
    archived_count = fields.Integer(string='Archived')
    skipped_count = fields.Integer(string='Skipped')
    error_count = fields.Integer(string='Errors')
    summary = fields.Html(string='Summary', readonly=True)
    error_details = fields.Text(string='Error Details', readonly=True)
    has_errors = fields.Boolean(string='Has Errors', compute='_compute_has_errors')

    @api.depends('error_count')
    def _compute_has_errors(self):
        for rec in self:
            rec.has_errors = bool(rec.error_count)
