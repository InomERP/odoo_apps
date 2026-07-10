from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    partner_credit_limit = fields.Monetary(
        related="partner_id.commercial_partner_id.x_credit_limit",
        string="Credit Limit", readonly=True)

    partner_credit_available = fields.Monetary(
        related="partner_id.commercial_partner_id.x_credit_available",
        string="Available Credit", readonly=True)

    x_credit_exceeded_amount = fields.Monetary(
        string="Exceeded Amount",
        compute="_compute_x_credit_exceeded_amount",
        store=False,
    )
    x_credit_stage = fields.Selection(
        selection=[
            ("draft", "Quotation"),
            ("sent", "Quotation Sent"),
            ("credit_limit", "Credit limit"),
            ("sale", "Sales Order"),
        ],
        string="Credit Stage",
        compute="_compute_x_credit_stage",
    )

    # --- Credit approval workflow ---
    credit_approval_request_ids = fields.One2many(
        "credit.approval.request", "sale_order_id",
        string="Credit Approval Requests",
    )
    credit_approval_count = fields.Integer(
        string="Credit Approval Count",
        compute="_compute_credit_approval_info",
    )
    active_credit_approval_id = fields.Many2one(
        "credit.approval.request", string="Latest Credit Approval",
        compute="_compute_credit_approval_info",
    )
    credit_approval_status = fields.Selection(
        selection=[
            ("none", "No Approval Needed"),
            ("pending", "Waiting Credit Approval"),
            ("approved", "Credit Approved"),
            ("rejected", "Credit Rejected"),
        ],
        string="Credit Approval Status",
        compute="_compute_credit_approval_info", store=True,
    )


    # --- Explicit, backend-driven gate for the Request Approval button ---
    is_credit_limit_exceeded = fields.Boolean(
        string="Credit Limit Exceeded",
        compute="_compute_credit_approval_gate", store=False,
        help="True when this order's total credit exposure exceeds the "
             "customer's credit limit.",
    )
    can_request_approval = fields.Boolean(
        string="Can Request Credit Approval",
        compute="_compute_credit_approval_gate", store=False,
        help="True only when the limit is exceeded, the order is still a "
             "quotation, and no approval is already pending/approved/rejected.",
    )

    @api.depends("x_credit_exceeded_amount", "state", "credit_approval_status")
    def _compute_credit_approval_gate(self):
        for order in self:
            # Reuse the existing exceeded-amount computation (no duplicate
            # exposure logic): exceeded iff excess > 0.
            exceeded = order.x_credit_exceeded_amount > 0
            order.is_credit_limit_exceeded = exceeded
            order.can_request_approval = (
                exceeded
                and order.state in ("draft", "sent")
                and order.credit_approval_status in ("none", "rejected")
            )
    @api.depends(
        "credit_approval_request_ids",
        "credit_approval_request_ids.state",
    )
    def _compute_credit_approval_info(self):
        for order in self:
            requests = order.credit_approval_request_ids
            order.credit_approval_count = len(requests)
            latest = requests.sorted("id")[-1] if requests else False
            order.active_credit_approval_id = latest.id if latest else False
            if not latest:
                order.credit_approval_status = "none"
            elif latest.state == "to_approve":
                order.credit_approval_status = "pending"
            elif latest.state == "approved":
                order.credit_approval_status = "approved"
            elif latest.state == "rejected":
                order.credit_approval_status = "rejected"
            else:
                order.credit_approval_status = "none"

    @api.depends("x_credit_exceeded_amount", "state")
    def _compute_x_credit_stage(self):
        for order in self:
            if order.x_credit_exceeded_amount > 0 and order.state != "sale":
                order.x_credit_stage = "credit_limit"
            elif order.state == "sale":
                order.x_credit_stage = "sale"
            elif order.state == "sent":
                order.x_credit_stage = "sent"
            else:
                order.x_credit_stage = "draft"
    @api.depends(
        "partner_id.commercial_partner_id.x_check_credit",
        "partner_id.commercial_partner_id.x_credit_limit",
        "partner_id.commercial_partner_id.x_credit_used",
        "amount_total",
        "order_line.product_uom_qty",
        "order_line.price_total",
        "state",
    )
    def _compute_x_credit_exceeded_amount(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if partner.x_check_credit and partner.x_credit_limit > 0:
                values = order._get_credit_values()
                order.x_credit_exceeded_amount = values["excess"]
            else:
                order.x_credit_exceeded_amount = 0

    # ------------------------------------------------------------------
    # Credit exposure
    # ------------------------------------------------------------------
    def _get_credit_values(self):
        """Compute the full credit exposure for this order.

        Exposure = open receivables (unpaid posted invoices)
                   + worth of other confirmed sale orders
                   + this order's total.
        Returns a dict reused by the compute, the wizard and the gate."""
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        receivables = partner.x_credit_used
        other_orders = self.env["sale.order"].search([
            ("partner_id.commercial_partner_id", "=", partner.id),
            ("state", "=", "sale"),
            ("id", "!=", self.id),
        ])
        confirmed_so = sum(other_orders.mapped("amount_total"))
        order_amount = self.amount_total
        exposure = receivables + confirmed_so + order_amount
        credit_limit = partner.x_credit_limit
        excess = max(0.0, exposure - credit_limit)
        return {
            "partner": partner,
            "credit_limit": credit_limit,
            "receivables": receivables,
            "confirmed_so": confirmed_so,
            "order_amount": order_amount,
            "exposure": exposure,
            "available": credit_limit - exposure,
            "excess": excess,
        }

    # ------------------------------------------------------------------
    # Confirmation gate
    # ------------------------------------------------------------------
    def action_confirm(self):
        if self.env.context.get("skip_credit_check"):
            return super().action_confirm()
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if not (partner.x_check_credit and partner.x_credit_limit > 0):
                continue
            values = order._get_credit_values()
            if values["exposure"] <= values["credit_limit"]:
                continue

            requests = order.credit_approval_request_ids
            if requests.filtered(lambda r: r.state == "approved"):
                # Already approved -> allow this order through
                continue
            if requests.filtered(lambda r: r.state == "to_approve"):
                raise UserError(_(
                    "Sale Order %s is waiting for credit approval. It cannot "
                    "be confirmed until a Credit Approval Manager approves the "
                    "request."
                ) % order.name)
            # No pending/approved request (covers fresh + previously rejected):
            # open the approval request wizard.
            return order._open_credit_approval_wizard(values)
        return super().action_confirm()

    def _open_credit_approval_wizard(self, values):
        self.ensure_one()
        wizard = self.env["sale.credit.limit.wizard"].create({
            "sale_order_id": self.id,
            "partner_id": values["partner"].id,
            "credit_limit": values["credit_limit"],
            "total_receivable": values["receivables"],
            "sale_orders_worth": values["confirmed_so"],
            "current_quotation": values["order_amount"],
            "available_credit": values["available"],
            "exceeded_amount": values["excess"],
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Credit Limit - Approval Request"),
            "res_model": "sale.credit.limit.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }
    # ------------------------------------------------------------------
    # Approval request (explicit header button)
    # ------------------------------------------------------------------
    def action_request_credit_approval(self):
        """Open the approval-request wizard from the Sale Order header.
        Reuses the same exposure calculation and wizard as the confirm gate,
        so there is a single source of truth and no duplicated logic."""
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        if not (partner.x_check_credit and partner.x_credit_limit > 0):
            raise UserError(_(
                "This customer has no credit limit to enforce."))
        values = self._get_credit_values()
        if values["exposure"] <= values["credit_limit"]:
            raise UserError(_(
                "This order is within the customer's credit limit; "
                "no approval is needed."))
        requests = self.credit_approval_request_ids
        if requests.filtered(lambda r: r.state == "to_approve"):
            raise UserError(_(
                "A credit approval request is already pending for this order."))
        if requests.filtered(lambda r: r.state == "approved"):
            raise UserError(_(
                "This order's credit has already been approved."))
        return self._open_credit_approval_wizard(values)

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_credit_status(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Credit Status"),
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": self.partner_id.commercial_partner_id.id,
        }
    
    def action_approve_credit_request(self):
        self.ensure_one()
        request = self.active_credit_approval_id
        if not request or request.state != "to_approve":
            raise UserError(_(
                "There is no pending credit approval request for this order."))
        return request.action_approve()

    def action_reject_credit_request(self):
        self.ensure_one()
        request = self.active_credit_approval_id
        if not request or request.state != "to_approve":
            raise UserError(_(
                "There is no pending credit approval request for this order."))
        return request.action_open_reject_wizard()
