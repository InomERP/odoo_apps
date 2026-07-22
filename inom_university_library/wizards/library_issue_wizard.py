# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import _, fields, models
from odoo.exceptions import UserError


class UnivLibraryIssueWizard(models.TransientModel):
    _name = "univ.library.issue.wizard"
    _description = "Issue Book"

    member_id = fields.Many2one(comodel_name="univ.library.member",
                                string="Member", required=True)
    barcode = fields.Char(string="Scan / Enter Copy Barcode", required=True)
    issue_date = fields.Date(string="Issue Date",
                             default=fields.Date.context_today, required=True)
    loan_days = fields.Integer(string="Loan Days", default=14)

    def action_issue(self):
        self.ensure_one()
        copy = self.env["univ.library.copy"].search(
            [("barcode", "=", self.barcode)], limit=1)
        if not copy:
            raise UserError(_("No copy with barcode %s.", self.barcode))
        if copy.state != "available":
            raise UserError(_("Copy is not available (%s).", copy.state))
        issue = self.env["univ.library.issue"].create({
            "copy_id": copy.id,
            "member_id": self.member_id.id,
            "issue_date": self.issue_date,
            "due_date": self.issue_date + timedelta(days=self.loan_days),
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.library.issue",
            "res_id": issue.id,
            "view_mode": "form",
            "target": "current",
        }
