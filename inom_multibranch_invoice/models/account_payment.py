# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    inom_branch_id = fields.Many2one(
        comodel_name="inom.branch", string="Branch",
        tracking=True, index=True, copy=True,
        domain="[('company_id', '=', company_id)]",
        default=lambda self: self.env.user.inom_default_branch_id.id or False,
        help="Operating unit / branch this payment belongs to.",
    )

    def _inom_sync_branch_to_move(self):
        for payment in self:
            if payment.move_id and payment.move_id.inom_branch_id != payment.inom_branch_id:
                payment.move_id.inom_branch_id = payment.inom_branch_id.id

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._inom_sync_branch_to_move()
        return payments

    def write(self, vals):
        res = super().write(vals)
        if "inom_branch_id" in vals:
            self._inom_sync_branch_to_move()
        return res

    def _inom_branch_from_reconciled(self):
        """Pick a branch from the invoices being paid, when not set manually."""
        for payment in self:
            if payment.inom_branch_id:
                continue
            reconciled = payment.reconciled_invoice_ids or payment.reconciled_bill_ids
            branch = reconciled.filtered("inom_branch_id")[:1].inom_branch_id
            if branch:
                payment.inom_branch_id = branch.id
                payment._inom_sync_branch_to_move()
