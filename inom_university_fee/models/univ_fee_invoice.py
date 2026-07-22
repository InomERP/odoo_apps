# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivFeeInvoice(models.Model):
    _name = "univ.fee.invoice"
    _description = "Student Fee Invoice"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Reference", copy=False, readonly=True,
        default=lambda self: _("New"),
    )
    student_id = fields.Many2one(
        comodel_name="univ.student",
        string="Student",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Bill-to Contact",
        related="student_id.partner_id",
        store=True,
    )
    structure_id = fields.Many2one(
        comodel_name="univ.fee.structure",
        string="Fee Structure",
        ondelete="restrict",
        index=True,
    )
    session_id = fields.Many2one(
        comodel_name="univ.academic.session", string="Academic Session",
        related="structure_id.session_id", store=True,
    )
    waiver_ids = fields.One2many(
        comodel_name="univ.fee.waiver",
        inverse_name="invoice_id",
        string="Waivers",
    )
    refund_ids = fields.One2many(
        comodel_name="univ.fee.refund.request",
        inverse_name="invoice_id",
        string="Refunds",
    )
    scholarship_award_ids = fields.One2many(
        comodel_name="univ.scholarship.award",
        inverse_name="invoice_id",
        string="Scholarships",
    )
    amount_waived = fields.Monetary(
        string="Waived", compute="_compute_adjustments", store=True,
        currency_field="currency_id",
    )
    amount_scholarship = fields.Monetary(
        string="Scholarship", compute="_compute_adjustments", store=True,
        currency_field="currency_id",
    )
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program",
        related="student_id.program_id", store=True, index=True,
    )
    batch_id = fields.Many2one(
        comodel_name="univ.batch", string="Batch",
        related="student_id.batch_id", store=True,
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester", string="Semester",
        related="student_id.semester_id", store=True,
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry / Invoice",
        copy=False,
        ondelete="restrict",
        index=True,
    )
    invoice_date = fields.Date(
        string="Invoice Date", related="move_id.invoice_date", store=True
    )
    due_date = fields.Date(
        string="Due Date", related="move_id.invoice_date_due", store=True
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", string="Currency",
        related="move_id.currency_id", store=True,
    )
    amount_total = fields.Monetary(
        string="Total", related="move_id.amount_total", store=True,
        currency_field="currency_id",
    )
    amount_paid = fields.Monetary(
        string="Paid", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )
    amount_residual = fields.Monetary(
        string="Residual", related="move_id.amount_residual", store=True,
        currency_field="currency_id",
    )
    move_state = fields.Selection(
        related="move_id.state", string="Move State", store=True
    )
    payment_state = fields.Selection(
        related="move_id.payment_state", string="Payment Status", store=True
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("open", "Open"),
            ("partial", "Partially Paid"),
            ("paid", "Paid"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        compute="_compute_state",
        store=True,
    )
    late_fee_accrued = fields.Monetary(
        string="Late Fee Accrued", default=0.0, currency_field="currency_id"
    )
    days_overdue = fields.Integer(
        string="Days Overdue", compute="_compute_aging", store=True
    )
    aging_bucket = fields.Selection(
        selection=[
            ("current", "Not Due / Current"),
            ("b1", "0-30 days"),
            ("b2", "30-60 days"),
            ("b3", "60+ days"),
        ],
        string="Aging Bucket",
        compute="_compute_aging",
        store=True,
    )
    installment_plan_id = fields.Many2one(
        comodel_name="univ.fee.installment.plan",
        string="Installment Plan",
        copy=False,
    )
    installment_count = fields.Integer(
        string="Installments", compute="_compute_installment_count"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (_("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.fee.invoice"
                ) or "FEE/0001"
        return super().create(vals_list)

    @api.depends("amount_total", "amount_residual")
    def _compute_amounts(self):
        for record in self:
            record.amount_paid = record.amount_total - record.amount_residual

    @api.depends("move_state", "payment_state")
    def _compute_state(self):
        for record in self:
            if not record.move_id or record.move_state == "draft":
                record.state = "draft"
            elif record.move_state == "cancel":
                record.state = "cancel"
            elif record.payment_state in ("paid", "in_payment", "reversed"):
                record.state = "paid"
            elif record.payment_state == "partial":
                record.state = "partial"
            else:
                record.state = "open"

    @api.depends("due_date", "payment_state", "move_state")
    def _compute_aging(self):
        today = fields.Date.context_today(self)
        for record in self:
            overdue = 0
            bucket = "current"
            if (
                record.move_state == "posted"
                and record.payment_state not in ("paid", "in_payment", "reversed")
                and record.due_date
                and record.due_date < today
            ):
                overdue = (today - record.due_date).days
                if overdue <= 30:
                    bucket = "b1"
                elif overdue <= 60:
                    bucket = "b2"
                else:
                    bucket = "b3"
            record.days_overdue = overdue
            record.aging_bucket = bucket

    def _compute_installment_count(self):
        for record in self:
            record.installment_count = len(
                record.installment_plan_id.line_ids
            )

    @api.depends(
        "waiver_ids.state", "waiver_ids.amount",
        "scholarship_award_ids.state", "scholarship_award_ids.amount",
    )
    def _compute_adjustments(self):
        for record in self:
            record.amount_waived = sum(
                record.waiver_ids.filtered(
                    lambda w: w.state == "applied"
                ).mapped("amount")
            )
            record.amount_scholarship = sum(
                record.scholarship_award_ids.filtered(
                    lambda a: a.state == "disbursed"
                ).mapped("amount")
            )

    # ------------------------------------------------------------------
    # Accounting helpers
    # ------------------------------------------------------------------
    def _get_fee_journal(self):
        self.ensure_one()
        journal = self.company_id.fee_journal_id
        if not journal:
            journal = self.env["account.journal"].search(
                [("type", "=", "sale"), ("company_id", "=", self.company_id.id)],
                limit=1,
            )
        if not journal:
            raise UserError(
                _(
                    "No sales journal found for %s. Configure Accounting first.",
                    self.company_id.display_name,
                )
            )
        return journal

    @api.model
    def _build_invoice_lines(self, structure):
        """Return account.move invoice_line_ids commands from a structure.

        Each fee head becomes its own invoice line. The structure line's
        discount is carried through Odoo's native ``discount`` field, so the
        invoice (form and PDF) shows the original amount, the discount % and
        the net subtotal per head, while accounting stays fully standard.
        """
        commands = []
        for line in structure.line_ids:
            head = line.head_id
            vals = {
                "name": head.name,
                "product_id": head.product_id.id,
                "quantity": 1.0,
                "price_unit": line.amount,
                "discount": line.discount_percent or 0.0,
            }
            account = head._get_income_account()
            if account:
                vals["account_id"] = account.id
            if head.tax_ids:
                vals["tax_ids"] = [(6, 0, head.tax_ids.ids)]
            commands.append((0, 0, vals))
        return commands

    @api.model
    def create_service_charge(self, student, head, amount, label=None,
                              due_date=None, post=True):
        """Fee-bridge API for campus-service modules.

        Raises a single-line fee charge (library fine, hostel/transport fee,
        certificate fee, etc.) on the student's ledger WITHOUT the caller ever
        touching account.move directly. Returns the univ.fee.invoice wrapper.
        """
        if not student or not head:
            raise UserError(_("A student and a fee head are required."))
        if amount <= 0:
            raise UserError(_("The charge amount must be positive."))
        if not student.partner_id:
            raise UserError(_(
                "Student %s has no linked contact.", student.display_name))
        wrapper = self.create({
            "student_id": student.id,
            "company_id": student.company_id.id or self.env.company.id,
        })
        line_vals = {
            "name": label or head.name,
            "product_id": head.product_id.id,
            "quantity": 1.0,
            "price_unit": amount,
        }
        account = head._get_income_account()
        if account:
            line_vals["account_id"] = account.id
        if head.tax_ids:
            line_vals["tax_ids"] = [(6, 0, head.tax_ids.ids)]
        today = fields.Date.context_today(self)
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": student.partner_id.id,
            "invoice_date": today,
            "invoice_date_due": due_date or today,
            "journal_id": wrapper._get_fee_journal().id,
            "invoice_origin": label or head.name,
            "invoice_line_ids": [(0, 0, line_vals)],
        })
        wrapper.move_id = move.id
        if post:
            move.action_post()
        return wrapper

    def action_post(self):
        for record in self:
            if record.move_id and record.move_state == "draft":
                record.move_id.action_post()
        return True

    def action_view_move(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("No journal entry is linked yet."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoice"),
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_register_payment(self):
        self.ensure_one()
        if not self.move_id or self.move_state != "posted":
            raise UserError(
                _("Post the invoice before registering a payment.")
            )
        return self.move_id.with_context(
            active_model="account.move", active_ids=self.move_id.ids
        ).action_register_payment()

    def action_open_installment_plan(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Installment Plan"),
            "res_model": "univ.fee.installment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_invoice_id": self.id},
        }

    def action_request_refund(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Refund Request"),
            "res_model": "univ.fee.refund.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_invoice_id": self.id},
        }

    def action_request_waiver(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fee Waiver"),
            "res_model": "univ.fee.waiver.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_invoice_id": self.id},
        }
