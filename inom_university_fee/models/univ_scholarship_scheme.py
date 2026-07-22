# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivScholarshipScheme(models.Model):
    _name = "univ.scholarship.scheme"
    _description = "Scholarship / Financial Aid Scheme"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Scheme", required=True, tracking=True)
    code = fields.Char(string="Code")
    aid_type = fields.Selection(
        selection=[
            ("scholarship", "Scholarship"),
            ("concession", "Concession"),
            ("financial_aid", "Financial Aid"),
        ],
        string="Type",
        default="scholarship",
        required=True,
    )
    amount_type = fields.Selection(
        selection=[("fixed", "Fixed Amount"), ("percent", "Percentage")],
        string="Computation",
        default="fixed",
        required=True,
    )
    amount = fields.Float(
        string="Amount / Percentage", required=True,
        help="Fixed amount, or a percentage of the fee invoice total.",
    )
    eligibility = fields.Text(string="Eligibility Criteria")
    min_category = fields.Selection(
        selection=[
            ("any", "Any"),
            ("general", "General"),
            ("obc", "OBC"),
            ("sc", "SC"),
            ("st", "ST"),
            ("ews", "EWS"),
        ],
        string="Applies to Category",
        default="any",
    )
    fund_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Scholarship Fund Account",
        help="Expense / contra account used when disbursing the award.",
    )
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True,
    )
    award_ids = fields.One2many(
        comodel_name="univ.scholarship.award",
        inverse_name="scheme_id",
        string="Awards",
    )
    award_count = fields.Integer(
        string="Awards", compute="_compute_award_count"
    )

    _sql_constraints = [
        ("code_uniq", "unique(code, company_id)",
         "The scheme code must be unique per company."),
    ]

    def _compute_award_count(self):
        data = self.env["univ.scholarship.award"]._read_group(
            [("scheme_id", "in", self.ids)],
            groupby=["scheme_id"],
            aggregates=["__count"],
        )
        mapped = {s.id: c for s, c in data}
        for scheme in self:
            scheme.award_count = mapped.get(scheme.id, 0)

    def compute_award_amount(self, invoice):
        """Return the award amount for a given fee invoice."""
        self.ensure_one()
        if self.amount_type == "percent":
            return (invoice.amount_total or 0.0) * self.amount / 100.0
        return self.amount

    def action_view_awards(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Awards"),
            "res_model": "univ.scholarship.award",
            "view_mode": "list,form",
            "domain": [("scheme_id", "=", self.id)],
            "context": {"default_scheme_id": self.id},
        }
