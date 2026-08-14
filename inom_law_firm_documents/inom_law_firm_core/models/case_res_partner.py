# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    law_case_count = fields.Integer(string="Case Count", compute="_compute_law_case_count")

    def _compute_law_case_count(self):
        Case = self.env["law.case"]
        for partner in self:
            partner.law_case_count = Case.search_count([("client_id", "=", partner.id)])

    def action_view_client_cases(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cases"),
            "res_model": "law.case",
            "domain": [("client_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"default_client_id": self.id},
        }
