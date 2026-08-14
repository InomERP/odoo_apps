# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class LawDocument(models.Model):
    _name = "law.document"
    _description = "Legal Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Title", required=True, tracking=True)
    reference = fields.Char(string="Document No.", copy=False, readonly=True, index=True)
    case_id = fields.Many2one("law.case", string="Case", required=True,
                              ondelete="cascade", tracking=True)
    document_type_id = fields.Many2one("law.document.type", string="Document Type")
    state = fields.Selection([
        ("draft", "Draft"), ("review", "Review"), ("approved", "Approved"),
        ("signed", "Signed"), ("archived", "Archived"), ("expired", "Expired"),
    ], default="draft", tracking=True, string="Status")
    confidential = fields.Boolean(string="Confidential", tracking=True)
    file = fields.Binary(string="File", attachment=True)
    filename = fields.Char(string="Filename")
    version_number = fields.Integer(string="Current Version", default=1, readonly=True)
    version_ids = fields.One2many("law.document.version", "document_id", string="Version History")
    issue_date = fields.Date(string="Issue Date")
    expiry_date = fields.Date(string="Expiry Date")
    responsible_id = fields.Many2one("res.users", string="Responsible",
                                     default=lambda self: self.env.user)
    description = fields.Text()
    company_id = fields.Many2one(related="case_id.company_id", store=True, index=True)
    active = fields.Boolean(default=True)

    @api.depends("case_id.case_number", "name", "version_number")
    def _compute_display_name(self):
        for doc in self:
            case = doc.case_id.case_number or doc.case_id.display_name or ''
            parts = [p for p in (case, doc.name or '') if p]
            parts.append("v%s" % (doc.version_number or 1))
            doc.display_name = " | ".join(parts)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                vals["reference"] = self.env["ir.sequence"].next_by_code("law.document") or "/"
        return super().create(vals_list)

    def action_save_version(self):
        """Snapshot the current file into an immutable version record."""
        for doc in self:
            if not doc.file:
                continue
            self.env["law.document.version"].create({
                "document_id": doc.id,
                "version_number": doc.version_number,
                "file": doc.file,
                "filename": doc.filename,
                "note": _("Snapshot of version %s") % doc.version_number,
            })
            doc.version_number += 1
        return True

    def action_review(self):
        self.write({"state": "review"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_sign(self):
        self.write({"state": "signed"})

    def action_archive_doc(self):
        self.write({"state": "archived"})

    def action_set_draft(self):
        self.write({"state": "draft"})
