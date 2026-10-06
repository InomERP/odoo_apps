from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_open_merge_wizard(self):
        if len(self) < 2:
            raise UserError(_("Please select at least two invoices to merge."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Merge Invoices"),
            "res_model": "invoice.merge.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_ids": self.ids,
                "active_model": "account.move",
            },
        }
