# -*- coding: utf-8 -*-
from odoo import fields, models


class LawCase(models.Model):
    _inherit = "law.case"

    document_count = fields.Integer(string="Document Count", compute="_compute_document_count")

    def _compute_document_count(self):
        Document = self.env["law.document"]
        for case in self:
            case.document_count = Document.search_count([("case_id", "=", case.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Documents",
            "res_model": "law.document",
            "domain": [("case_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"default_case_id": self.id},
        }
