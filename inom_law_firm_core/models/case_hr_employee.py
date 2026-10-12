# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    active_case_count = fields.Integer(string="Active Cases", compute="_compute_active_case_count")

    def _compute_active_case_count(self):
        Case = self.env["law.case"]
        for emp in self:
            emp.active_case_count = Case.search_count([
                ("lawyer_id", "=", emp.id), ("is_closed", "=", False),
            ])

    def action_view_lawyer_cases(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Cases",
            "res_model": "law.case",
            "domain": [("lawyer_id", "=", self.id)],
            "view_mode": "list,kanban,form",
            "context": {"default_lawyer_id": self.id},
        }
