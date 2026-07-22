# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class UnivFeeStructure(models.Model):
    _name = "univ.fee.structure"
    _description = "Fee Structure"
    _inherit = ["mail.thread"]
    _order = "program_id, semester_id, id"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code")
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    batch_id = fields.Many2one(
        comodel_name="univ.batch",
        string="Batch",
        ondelete="restrict",
        index=True,
        help="Leave empty to apply to every batch of the program.",
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester",
        string="Semester",
        ondelete="restrict",
        index=True,
        help="Leave empty for a program-wide (annual) structure.",
    )
    session_id = fields.Many2one(
        comodel_name="univ.academic.session",
        string="Academic Session",
        ondelete="restrict",
        index=True,
    )
    quota_id = fields.Many2one(
        comodel_name="univ.fee.quota",
        string="Quota",
        ondelete="restrict",
        help="Leave empty to apply to every quota.",
    )
    category = fields.Selection(
        selection=[
            ("all", "All Categories"),
            ("general", "General"),
            ("obc", "OBC"),
            ("sc", "SC"),
            ("st", "ST"),
            ("ews", "EWS"),
            ("other", "Other"),
        ],
        string="Student Category",
        default="all",
        required=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("confirmed", "Confirmed")],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="univ.fee.structure.line",
        inverse_name="structure_id",
        string="Fee Heads",
        copy=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    amount_gross = fields.Monetary(
        string="Total Fee", compute="_compute_amount_total", store=True,
        currency_field="currency_id",
    )
    discount_total = fields.Monetary(
        string="Total Discount", compute="_compute_amount_total", store=True,
        currency_field="currency_id",
    )
    amount_total = fields.Monetary(
        string="Net Payable", compute="_compute_amount_total", store=True,
        currency_field="currency_id",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(string="Active", default=True)
    invoice_count = fields.Integer(
        string="Invoices", compute="_compute_invoice_count"
    )

    @api.depends("line_ids.amount", "line_ids.discount_amount",
                 "line_ids.net_amount")
    def _compute_amount_total(self):
        for structure in self:
            structure.amount_gross = sum(structure.line_ids.mapped("amount"))
            structure.discount_total = sum(
                structure.line_ids.mapped("discount_amount")
            )
            structure.amount_total = sum(
                structure.line_ids.mapped("net_amount")
            )

    def _compute_invoice_count(self):
        data = self.env["univ.fee.invoice"]._read_group(
            [("structure_id", "in", self.ids)],
            groupby=["structure_id"],
            aggregates=["__count"],
        )
        mapped = {s.id: c for s, c in data}
        for structure in self:
            structure.invoice_count = mapped.get(structure.id, 0)

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fee Invoices"),
            "res_model": "univ.fee.invoice",
            "view_mode": "list,form",
            "domain": [("structure_id", "=", self.id)],
            "context": {"default_structure_id": self.id},
        }


class UnivFeeStructureLine(models.Model):
    _name = "univ.fee.structure.line"
    _description = "Fee Structure Line"
    _order = "sequence, id"

    structure_id = fields.Many2one(
        comodel_name="univ.fee.structure",
        string="Structure",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    head_id = fields.Many2one(
        comodel_name="univ.fee.head",
        string="Fee Head",
        required=True,
        ondelete="restrict",
    )
    amount = fields.Monetary(
        string="Amount", required=True, currency_field="currency_id"
    )
    discount_percent = fields.Float(string="Discount %", default=0.0)
    discount_amount = fields.Monetary(
        string="Discount Amount",
        compute="_compute_discount",
        store=True,
        currency_field="currency_id",
    )
    net_amount = fields.Monetary(
        string="Net Amount",
        compute="_compute_discount",
        store=True,
        currency_field="currency_id",
    )
    collect_at_admission = fields.Boolean(
        string="Collect at Admission",
        default=True,
        help="Include this fee head in the admission deposit invoice "
             "(charged at the structure's Deposit %). Unticked heads are "
             "billed later through the normal fee collection process.",
    )
    currency_id = fields.Many2one(
        related="structure_id.currency_id", string="Currency"
    )

    @api.depends("amount", "discount_percent")
    def _compute_discount(self):
        for line in self:
            discount = line.amount * (line.discount_percent or 0.0) / 100.0
            line.discount_amount = discount
            line.net_amount = line.amount - discount

    _sql_constraints = [
        ("structure_head_uniq", "unique(structure_id, head_id)",
         "A fee head can only appear once per structure."),
    ]
