from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class CreditApprovalRequest(models.Model):
    """Persistent approval request raised when a Sale Order exceeds the
    customer's credit limit. It carries the full credit exposure snapshot,
    drives the approve/reject workflow and keeps a full chatter trail."""

    _name = "credit.approval.request"
    _description = "Customer Credit Approval Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        default="/", index=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order", string="Sale Order", required=True,
        ondelete="cascade", tracking=True, index=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Company",
        default=lambda self: self.env.company, required=True,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency",
        related="sale_order_id.currency_id", store=True, readonly=True,
    )

    # --- Credit exposure snapshot (captured at submission time) ---
    credit_limit = fields.Monetary(string="Credit Limit", readonly=True)
    outstanding_amount = fields.Monetary(
        string="Current Outstanding Amount", readonly=True,
        help="Total open/unpaid posted customer invoices (receivables).")
    confirmed_so_amount = fields.Monetary(
        string="Confirmed Sale Orders", readonly=True,
        help="Worth of other already-confirmed sale orders for this customer.")
    order_amount = fields.Monetary(string="Sale Order Amount", readonly=True)
    available_credit = fields.Monetary(string="Available Credit", readonly=True)
    excess_amount = fields.Monetary(string="Excess Amount", readonly=True)
    reason = fields.Text(string="Reason / Notes")

    state = fields.Selection(
        selection=[
            ("to_approve", "Waiting Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status", default="to_approve", required=True,
        tracking=True, index=True,
    )

    # --- Request audit ---
    requested_by = fields.Many2one(
        "res.users", string="Requested By",
        default=lambda self: self.env.user, readonly=True, tracking=True,
    )
    request_date = fields.Datetime(
        string="Request Date", default=fields.Datetime.now, readonly=True,
    )

    # --- Approval audit ---
    approved_by = fields.Many2one(
        "res.users", string="Approved By", readonly=True, tracking=True,
    )
    approval_date = fields.Datetime(string="Approval Date", readonly=True)
    approval_notes = fields.Text(string="Approval Notes")

    # --- Rejection audit ---
    rejected_by = fields.Many2one(
        "res.users", string="Rejected By", readonly=True, tracking=True,
    )
    rejection_date = fields.Datetime(string="Rejection Date", readonly=True)
    rejection_reason = fields.Text(string="Rejection Reason", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "credit.approval.request"
                ) or "/"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_approver_users(self):
        group = self.env.ref(
            "inom_customer_credit_limit.group_credit_approval_manager",
            raise_if_not_found=False,
        )
        if not group:
            return self.env["res.users"]
        return self.env["res.users"].search([
            ("group_ids", "in", [group.id]),
            ("active", "=", True),
        ])

    def _check_approver(self):
        """Guard server-side: only credit approval managers can decide."""
        if not self.env.user.has_group(
            "inom_customer_credit_limit.group_credit_approval_manager"
        ):
            raise AccessError(_(
                "Only a Credit Approval Manager can approve or reject "
                "credit approval requests."
            ))

    def _credit_email_values(self, recipient_email):
        return {"email_to": recipient_email} if recipient_email else {}

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _notify_approvers(self):
        """Notify approvers on submission: chatter + inbox activity + email."""
        self.ensure_one()
        approvers = self._get_approver_users()

        # Chatter trail on both the request and the originating sale order
        body = _(
            "Credit approval requested for %(order)s. "
            "Excess amount: %(excess)s. Waiting for approval."
        ) % {
            "order": self.sale_order_id.name,
            "excess": self.excess_amount,
        }
        self.message_post(body=body, subtype_xmlid="mail.mt_note")
        self.sale_order_id.message_post(body=body, subtype_xmlid="mail.mt_note")

        # Inbox to-do activity for each approver
        for user in approvers:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=_("Credit Approval Required"),
                note=_(
                    "Sale Order %(order)s for %(customer)s requires credit "
                    "approval. Excess: %(excess)s."
                ) % {
                    "order": self.sale_order_id.name,
                    "customer": self.partner_id.name,
                    "excess": self.excess_amount,
                },
                user_id=user.id,
            )

        # Direct inbox notification (bell icon) to the approvers
        if approvers:
            self.message_notify(
                partner_ids=approvers.partner_id.ids,
                subject=_("Credit Approval Required - %s") % self.sale_order_id.name,
                body=body,
            )

        # Professional email to approvers
        template = self.env.ref(
            "inom_customer_credit_limit.mail_template_credit_approval_request",
            raise_if_not_found=False,
        )
        if template and approvers:
            emails = ",".join(approvers.filtered("email").mapped("email"))
            if emails:
                template.send_mail(
                    self.id, force_send=True,
                    email_values=self._credit_email_values(emails),
                )
        return True

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_approve(self):
        self.ensure_one()
        self._check_approver()
        if self.state != "to_approve":
            raise UserError(_("Only requests waiting for approval can be approved."))

        self.write({
            "state": "approved",
            "approved_by": self.env.user.id,
            "approval_date": fields.Datetime.now(),
        })

        notes = self.approval_notes or _("No additional notes.")
        chatter_body = _(
            "Credit limit override approved by %(user)s.<br/>Notes: %(notes)s"
        ) % {"user": self.env.user.name, "notes": notes}
        self.message_post(body=chatter_body, subtype_xmlid="mail.mt_note")

        # Close any pending approval activities on this request
        self.activity_unlink(["mail.mail_activity_data_todo"])

        # Approval email to the salesperson / requester
        template = self.env.ref(
            "inom_customer_credit_limit.mail_template_credit_approval_approved",
            raise_if_not_found=False,
        )
        if template:
            recipient = self.sale_order_id.user_id.email or self.requested_by.email
            template.send_mail(
                self.id, force_send=True,
                email_values=self._credit_email_values(recipient),
            )

        # Auto-confirm the sale order, bypassing the credit gate (already approved)
        self.sale_order_id.with_context(skip_credit_check=True).action_confirm()
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        self._check_approver()
        if self.state != "to_approve":
            raise UserError(_("Only requests waiting for approval can be rejected."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Credit Approval"),
            "res_model": "credit.approval.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_approval_request_id": self.id},
        }

    def _do_reject(self, reason):
        self.ensure_one()
        self._check_approver()
        if not reason:
            raise ValidationError(_("A rejection reason is required."))

        self.write({
            "state": "rejected",
            "rejected_by": self.env.user.id,
            "rejection_date": fields.Datetime.now(),
            "rejection_reason": reason,
        })

        chatter_body = _(
            "Credit limit override rejected by %(user)s.<br/>Reason: %(reason)s"
        ) % {"user": self.env.user.name, "reason": reason}
        self.message_post(body=chatter_body, subtype_xmlid="mail.mt_note")
        self.sale_order_id.message_post(body=chatter_body, subtype_xmlid="mail.mt_note")

        # Close any pending approval activities on this request
        self.activity_unlink(["mail.mail_activity_data_todo"])

        # Rejection email to the salesperson / requester
        template = self.env.ref(
            "inom_customer_credit_limit.mail_template_credit_approval_rejected",
            raise_if_not_found=False,
        )
        if template:
            recipient = self.sale_order_id.user_id.email or self.requested_by.email
            template.send_mail(
                self.id, force_send=True,
                email_values=self._credit_email_values(recipient),
            )
        return True

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sale Order"),
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": self.sale_order_id.id,
            "target": "current",
        }