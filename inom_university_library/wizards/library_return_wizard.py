# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class UnivLibraryReturnWizard(models.TransientModel):
    _name = "univ.library.return.wizard"
    _description = "Return Book"

    barcode = fields.Char(string="Scan / Enter Copy Barcode", required=True)

    def action_return(self):
        self.ensure_one()
        copy = self.env["univ.library.copy"].search(
            [("barcode", "=", self.barcode)], limit=1)
        if not copy:
            raise UserError(_("No copy with barcode %s.", self.barcode))
        issue = self.env["univ.library.issue"].search([
            ("copy_id", "=", copy.id), ("state", "in", ("issued", "overdue"))],
            limit=1)
        if not issue:
            raise UserError(_("No open issue for this copy."))
        issue.action_return()
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.library.issue",
            "res_id": issue.id,
            "view_mode": "form",
            "target": "current",
        }
