# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class LawEvidence(models.Model):
    _name = "law.evidence"
    _description = "Evidence"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Title", required=True, tracking=True)
    reference = fields.Char(string="Evidence No.", copy=False, readonly=True, index=True)
    case_id = fields.Many2one("law.case", string="Case", required=True,
                              ondelete="cascade", tracking=True)
    evidence_type = fields.Selection([
        ("physical", "Physical"), ("digital", "Digital"), ("photo", "Photo"),
        ("video", "Video"), ("audio", "Audio"), ("document", "Document"),
    ], string="Type", default="physical", required=True)
    source = fields.Char(string="Source / Collected From")
    collected_date = fields.Date(string="Collected On")
    collected_by = fields.Char(string="Collected By")
    current_custodian = fields.Char(string="Current Custodian")
    description = fields.Text()
    attachment_ids = fields.Many2many("ir.attachment", string="Files (photo/video/audio/doc)")
    related_document_ids = fields.Many2many("law.document", string="Related Documents")
    custody_log_ids = fields.One2many("law.evidence.log", "evidence_id",
                                      string="Chain of Custody")
    company_id = fields.Many2one(related="case_id.company_id", store=True, index=True)
    active = fields.Boolean(default=True)

    @api.depends("reference", "name")
    def _compute_display_name(self):
        for evidence in self:
            parts = [p for p in (evidence.reference, evidence.name) if p]
            evidence.display_name = " | ".join(parts) or _("Evidence")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                vals["reference"] = self.env["ir.sequence"].next_by_code("law.evidence") or "/"
        return super().create(vals_list)
