from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_credit_limit = fields.Monetary(
        string="Credit Limit",
        currency_field="currency_id",
        help="Maximum outstanding credit allowed for this customer. "
             "Leave 0 for no limit.",
    )

    x_credit_used = fields.Monetary(
        string="Credit Used",
        currency_field="currency_id",
        compute="_compute_x_credit_used",
        store=True,
    )

    x_credit_available = fields.Monetary(
        string="Available Credit",
        currency_field="currency_id",
        compute="_compute_x_credit_used",
        store=True,
    )

    x_check_credit = fields.Boolean(
        string="Check Credit",
        default=True,
        help="If unchecked, this customer's orders will never be blocked, "
             "even if the credit limit is exceeded.",
    )

    @api.depends(
        "x_credit_limit",
        "invoice_ids.amount_residual",
        "invoice_ids.state",
        "invoice_ids.payment_state",
    )
    def _compute_x_credit_used(self):
        for partner in self:
            open_invoices = self.env["account.move"].search([
                ("partner_id", "child_of", partner.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial")),
            ])
            used = sum(open_invoices.mapped("amount_residual"))
            partner.x_credit_used = used
            partner.x_credit_available = partner.x_credit_limit - used