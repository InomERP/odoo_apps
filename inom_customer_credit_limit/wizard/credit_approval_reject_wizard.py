from odoo import fields, models


class CreditApprovalRejectWizard(models.TransientModel):
    """Small wizard used by a Credit Approval Manager to capture the
    mandatory rejection reason before rejecting a credit approval request."""

    _name = "credit.approval.reject.wizard"
    _description = "Credit Approval Rejection Reason"

    approval_request_id = fields.Many2one(
        "credit.approval.request", string="Approval Request",
        required=True, readonly=True,
    )
    rejection_reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.approval_request_id._do_reject(self.rejection_reason)
        return {"type": "ir.actions.act_window_close"}