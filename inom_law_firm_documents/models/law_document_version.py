# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LawDocumentVersion(models.Model):
    _name = "law.document.version"
    _description = "Document Version (immutable)"
    _order = "version_number desc, id desc"

    document_id = fields.Many2one("law.document", required=True, ondelete="restrict")
    version_number = fields.Integer(string="Version", readonly=True)
    file = fields.Binary(string="File", attachment=True, readonly=True)
    filename = fields.Char(string="Filename", readonly=True)
    created_on = fields.Datetime(string="Saved On", default=fields.Datetime.now, readonly=True)
    created_by = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    note = fields.Char(readonly=True)

    @api.depends("document_id.name", "version_number", "created_on")
    def _compute_display_name(self):
        for version in self:
            doc_name = version.document_id.name or _("Document")
            name = "%s v%s" % (doc_name, version.version_number or 1)
            if version.created_on:
                name = "%s (%s)" % (name, version.created_on.strftime('%Y-%m-%d'))
            version.display_name = name

    def write(self, vals):
        raise UserError(_("Document versions are immutable and cannot be edited."))

    def unlink(self):
        raise UserError(_("Document versions are immutable and cannot be deleted."))
