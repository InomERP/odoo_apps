from odoo import fields, models, _


class SaleCreditLimitWizard(models.TransientModel):
    """Approval-request wizard shown when a Sale Order exceeds the customer's
    credit limit on confirmation. Instead of confirming directly, the user
    submits the order for credit approval."""

    _name = "sale.credit.limit.wizard"
    _description = "Customer Credit Limit Approval Request"

    sale_order_id = fields.Many2one("sale.order", required=True, readonly=True)
    partner_id = fields.Many2one(
        "res.partner", string="Customer", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", related="sale_order_id.currency_id")

    credit_limit = fields.Monetary(readonly=True)
    total_receivable = fields.Monetary(
        string="Current Outstanding Amount", readonly=True,
        help="Total open/unpaid posted invoice amount for this customer.")
    sale_orders_worth = fields.Monetary(
        string="Other Confirmed Sale Orders", readonly=True)
    current_quotation = fields.Monetary(
        string="Sale Order Amount", readonly=True)
    available_credit = fields.Monetary(
        string="Available Credit", readonly=True)
    exceeded_amount = fields.Monetary(
        string="Excess Amount", readonly=True)
    reason = fields.Text(string="Reason / Notes")

    def action_submit_for_approval(self):
        """Create the persistent approval request, link it to the order and
        notify the approvers. The order stays a quotation (it is blocked from
        confirming) until a Credit Approval Manager approves the request."""
        self.ensure_one()
        order = self.sale_order_id
        request = self.env["credit.approval.request"].create({
            "sale_order_id": order.id,
            "partner_id": self.partner_id.id,
            "credit_limit": self.credit_limit,
            "outstanding_amount": self.total_receivable,
            "confirmed_so_amount": self.sale_orders_worth,
            "order_amount": self.current_quotation,
            "available_credit": self.available_credit,
            "excess_amount": self.exceeded_amount,
            "reason": self.reason,
        })
        request._notify_approvers()
        return {
            "type": "ir.actions.act_window",
            "name": _("Quotations"),
            "res_model": "sale.order",
            "view_mode": "form,list",
            "res_id": order.id,
            "target": "current",
        }

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}