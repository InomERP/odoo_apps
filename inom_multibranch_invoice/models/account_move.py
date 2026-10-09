# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    inom_branch_id = fields.Many2one(
        comodel_name="inom.branch", string="Branch",
        tracking=True, index=True, copy=True,
        domain="[('company_id', '=', company_id)]",
        default=lambda self: self._inom_default_branch(),
        help="Operating unit / branch this document belongs to.",
    )
    inom_branch_doc_no = fields.Char(
        string="Branch Document No.", copy=False, readonly=True, index=True,
        help="Branch wise running number, assigned at posting when branch "
             "wise numbering is enabled.",
    )

    @api.model
    def _inom_default_branch(self):
        return self.env.user.inom_default_branch_id.id or False

    def _inom_assign_branch_doc_no(self):
        """Assign a branch document number at posting time when configured."""
        for move in self:
            branch = move.inom_branch_id
            if not branch or not branch.use_own_sequence:
                continue
            if move.inom_branch_doc_no:
                continue
            number = branch.next_document_number()
            if number:
                move.inom_branch_doc_no = number

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        posted._inom_assign_branch_doc_no()
        return posted

    @api.onchange("company_id")
    def _onchange_company_clear_branch(self):
        for move in self:
            if move.inom_branch_id and move.inom_branch_id.company_id != move.company_id:
                move.inom_branch_id = False
