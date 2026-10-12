# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivFeeInstallmentPlan(models.Model):
    _name = "univ.fee.installment.plan"
    _description = "Fee Installment Plan"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char(
        string="Reference", copy=False, readonly=True,
        default=lambda self: self.env._("New"),
    )
    invoice_id = fields.Many2one(
        comodel_name="univ.fee.invoice",
        string="Fee Invoice",
        required=True,
        ondelete="cascade",
        index=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student",
        related="invoice_id.student_id", store=True,
    )
    frequency = fields.Selection(
        selection=[
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
        ],
        string="Frequency",
        default="monthly",
        required=True,
    )
    count = fields.Integer(string="Installments", default=3, required=True)
    start_date = fields.Date(
        string="First Due Date", default=fields.Date.context_today, required=True
    )
    amount_total = fields.Monetary(
        string="Plan Amount", currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        related="invoice_id.currency_id", string="Currency"
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Completed"),
            ("default", "Defaulted"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="univ.fee.installment.line",
        inverse_name="plan_id",
        string="Schedule",
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="invoice_id.company_id", store=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (self.env._("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.fee.installment.plan"
                ) or "EMI/0001"
        return super().create(vals_list)

    def generate_schedule(self):
        """(Re)build EMI lines splitting the amount across the period."""
        self.ensure_one()
        if self.count <= 0:
            raise UserError(self.env._("Installment count must be positive."))
        self.line_ids.unlink()
        total = self.amount_total or self.invoice_id.amount_residual
        per = self.currency_id.round(total / self.count) if self.currency_id \
            else round(total / self.count, 2)
        step = 1 if self.frequency == "monthly" else 3
        lines = []
        allocated = 0.0
        for index in range(self.count):
            due = self.start_date + relativedelta(months=step * index)
            amount = per
            if index == self.count - 1:
                amount = total - allocated  # absorb rounding on the last line
            allocated += amount
            lines.append(
                (0, 0, {
                    "sequence": index + 1,
                    "due_date": due,
                    "amount": amount,
                })
            )
        self.line_ids = lines
        return True

    def action_confirm(self):
        for plan in self:
            if not plan.line_ids:
                plan.generate_schedule()
            plan.state = "confirmed"

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    @api.model
    def _cron_detect_defaults(self):
        today = fields.Date.today()
        plans = self.search([("state", "=", "confirmed")])
        for plan in plans:
            overdue = plan.line_ids.filtered(
                lambda l: l.state != "paid" and l.due_date and l.due_date < today
            )
            if overdue:
                overdue.filtered(lambda l: l.state != "overdue").write(
                    {"state": "overdue"}
                )
                plan.state = "default"
            elif all(l.state == "paid" for l in plan.line_ids):
                plan.state = "done"


class UnivFeeInstallmentLine(models.Model):
    _name = "univ.fee.installment.line"
    _description = "Fee Installment Line"
    _order = "plan_id, sequence, due_date"

    plan_id = fields.Many2one(
        comodel_name="univ.fee.installment.plan",
        string="Plan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="No.", default=1)
    due_date = fields.Date(string="Due Date", required=True)
    amount = fields.Monetary(string="Amount", currency_field="currency_id")
    currency_id = fields.Many2one(
        related="plan_id.currency_id", string="Currency"
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("overdue", "Overdue"),
        ],
        string="Status",
        default="pending",
        required=True,
    )
    paid_date = fields.Date(string="Paid On")

    def action_mark_paid(self):
        self.write({"state": "paid", "paid_date": fields.Date.context_today(self)})
