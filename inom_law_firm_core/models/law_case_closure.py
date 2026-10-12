# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LawCaseClosure(models.Model):
    _name = "law.case.closure"
    _description = "Case Closure Checklist"
    _order = "closure_date desc, id desc"

    case_id = fields.Many2one("law.case", string="Case", required=True, ondelete="cascade")
    state = fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed")],
                             default="draft", string="Status")
    final_hearing_done = fields.Boolean("Final hearing completed")
    documents_archived = fields.Boolean("Documents archived")
    final_invoice_generated = fields.Boolean("Final invoice generated")
    outstanding_checked = fields.Boolean("Outstanding balance checked")
    trust_settled = fields.Boolean("Trust balance settled")
    client_notified = fields.Boolean("Client notified")
    closure_reason = fields.Text("Closure reason")
    closure_date = fields.Date(default=fields.Date.context_today)
    closed_by_id = fields.Many2one("res.users", string="Closed By",
                                   default=lambda self: self.env.user)

    def action_confirm(self):
        self.ensure_one()
        checklist = {
            "Final hearing completed": self.final_hearing_done,
            "Documents archived": self.documents_archived,
            "Final invoice generated": self.final_invoice_generated,
            "Outstanding balance checked": self.outstanding_checked,
            "Trust balance settled": self.trust_settled,
            "Client notified": self.client_notified,
        }
        missing = [label for label, done in checklist.items() if not done]
        if not self.closure_reason:
            missing.append("Closure reason recorded")
        if missing:
            raise UserError(_("Cannot close the case. Outstanding checklist items:\n- %s")
                            % "\n- ".join(missing))
        self.state = "confirmed"
        closing_stage = self.env.ref("inom_law_firm_core.stage_closed", raise_if_not_found=False)
        if closing_stage:
            self.case_id.stage_id = closing_stage.id
        self.case_id.date_closed = fields.Date.context_today(self)
        return {"type": "ir.actions.act_window_close"}
