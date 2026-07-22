# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class UnivStudent(models.Model):
    _inherit = "univ.student"

    fee_invoice_ids = fields.One2many(
        comodel_name="univ.fee.invoice",
        inverse_name="student_id",
        string="Fee Invoices",
    )
    fee_invoice_count = fields.Integer(
        string="Fee Invoices", compute="_compute_fee_totals"
    )
    total_invoiced = fields.Monetary(
        string="Total Invoiced", compute="_compute_fee_totals",
        currency_field="company_currency_id",
    )
    total_paid = fields.Monetary(
        string="Total Paid", compute="_compute_fee_totals",
        currency_field="company_currency_id",
    )
    outstanding_amount = fields.Monetary(
        string="Outstanding", compute="_compute_fee_totals",
        currency_field="company_currency_id",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Company Currency",
        related="company_id.currency_id",
    )
    is_fee_defaulter = fields.Boolean(
        string="Fee Defaulter", default=False, copy=False, tracking=True,
        help="Flagged by the daily cron when dues cross the configured aging "
             "threshold. Consumed by other modules to gate services.",
    )
    fee_quota_id = fields.Many2one(
        comodel_name="univ.fee.quota", string="Quota",
        help="Admission quota used to match the applicable fee structure.",
    )
    total_scholarship = fields.Monetary(
        string="Total Scholarship", compute="_compute_fee_totals",
        currency_field="company_currency_id",
    )
    total_waived = fields.Monetary(
        string="Total Waived", compute="_compute_fee_totals",
        currency_field="company_currency_id",
    )

    @api.depends(
        "fee_invoice_ids.amount_total",
        "fee_invoice_ids.amount_residual",
        "fee_invoice_ids.move_state",
        "fee_invoice_ids.amount_scholarship",
        "fee_invoice_ids.amount_waived",
    )
    def _compute_fee_totals(self):
        for student in self:
            invoices = student.fee_invoice_ids.filtered(
                lambda i: i.move_state == "posted"
            )
            student.fee_invoice_count = len(student.fee_invoice_ids)
            student.total_invoiced = sum(invoices.mapped("amount_total"))
            student.total_paid = sum(
                i.amount_total - i.amount_residual for i in invoices
            )
            student.outstanding_amount = sum(invoices.mapped("amount_residual"))
            student.total_scholarship = sum(
                invoices.mapped("amount_scholarship")
            )
            student.total_waived = sum(invoices.mapped("amount_waived"))

    def action_view_fee_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Fee Invoices"),
            "res_model": "univ.fee.invoice",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }

    def action_view_ledger(self):
        """Open the receivable ledger (account.move.line) for this student."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Student Ledger"),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "=", self.partner_id.id),
                ("account_id.account_type", "=", "asset_receivable"),
                ("parent_state", "=", "posted"),
            ],
            "context": {"search_default_group_by_move": 1},
        }

    def get_ledger_lines(self):
        """Return chronological ledger rows with a running balance.

        Reads receivable journal items so the statement reflects the true
        accounting position (invoices debit, payments/credit notes credit).
        """
        self.ensure_one()
        if not self.partner_id:
            return []
        lines = self.env["account.move.line"].search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("account_id.account_type", "=", "asset_receivable"),
                ("parent_state", "=", "posted"),
            ],
            order="date asc, id asc",
        )
        rows = []
        balance = 0.0
        for line in lines:
            balance += line.debit - line.credit
            rows.append({
                "date": line.date,
                "reference": line.move_id.name,
                "label": line.name or line.move_id.ref or "",
                "debit": line.debit,
                "credit": line.credit,
                "balance": balance,
            })
        return rows

    # ------------------------------------------------------------------
    # Scheduled actions
    # ------------------------------------------------------------------
    @api.model
    def _cron_accrue_late_fees(self):
        Invoice = self.env["univ.fee.invoice"]
        today = fields.Date.today()
        invoices = Invoice.search(
            [
                ("move_state", "=", "posted"),
                ("payment_state", "not in", ("paid", "in_payment", "reversed")),
                ("due_date", "<", today),
            ]
        )
        for invoice in invoices:
            company = invoice.company_id
            rate = company.fee_late_fee_rate or 0.0
            if not rate:
                continue
            days = (today - invoice.due_date).days
            accrued = rate * days
            cap = company.fee_late_fee_cap or 0.0
            if cap:
                accrued = min(accrued, cap)
            if invoice.late_fee_accrued != accrued:
                invoice.late_fee_accrued = accrued

    @api.model
    def _cron_flag_defaulters(self):
        today = fields.Date.today()
        students = self.search([("active", "=", True)])
        for student in students:
            threshold = student.company_id.fee_defaulter_days or 60
            overdue = student.fee_invoice_ids.filtered(
                lambda i: i.move_state == "posted"
                and i.amount_residual > 0
                and i.due_date
                and (today - i.due_date).days >= threshold
            )
            flag = bool(overdue)
            if student.is_fee_defaulter != flag:
                student.is_fee_defaulter = flag

    @api.model
    def _cron_send_fee_reminders(self):
        Invoice = self.env["univ.fee.invoice"]
        Log = self.env["univ.fee.reminder.log"]
        today = fields.Date.today()
        thresholds = {7: "d7", 15: "d15", 30: "d30"}
        invoices = Invoice.search(
            [
                ("move_state", "=", "posted"),
                ("payment_state", "not in", ("paid", "in_payment", "reversed")),
                ("due_date", "<", today),
            ]
        )
        template = self.env.ref(
            "inom_university_fee.email_template_fee_reminder",
            raise_if_not_found=False,
        )
        for invoice in invoices:
            days = (today - invoice.due_date).days
            for limit, milestone in thresholds.items():
                if days < limit:
                    continue
                already = Log.search_count(
                    [("invoice_id", "=", invoice.id), ("milestone", "=", milestone)]
                )
                if already:
                    continue
                channel = "email"
                if milestone == "d30":
                    channel = "activity"
                    invoice.activity_schedule(
                        "mail.mail_activity_data_todo",
                        summary=self.env._("Fee overdue 30+ days: follow up"),
                    )
                elif template and invoice.partner_id.email:
                    template.send_mail(invoice.id, force_send=False)
                Log.create(
                    {
                        "invoice_id": invoice.id,
                        "milestone": milestone,
                        "channel": channel,
                    }
                )
