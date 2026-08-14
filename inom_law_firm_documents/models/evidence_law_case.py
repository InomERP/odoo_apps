# -*- coding: utf-8 -*-
from odoo import fields, models


class LawCase(models.Model):
    _inherit = "law.case"

    evidence_count = fields.Integer(string="Evidence Count", compute="_compute_evidence_count")

    def _compute_evidence_count(self):
        Evidence = self.env["law.evidence"]
        for case in self:
            case.evidence_count = Evidence.search_count([("case_id", "=", case.id)])

    def action_view_evidence(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Evidence",
            "res_model": "law.evidence",
            "domain": [("case_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"default_case_id": self.id},
        }
