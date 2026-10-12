# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UnivAdmissionRound(models.Model):
    _name = "univ.admission.round"
    _description = "Admission Round / Cycle"
    _inherit = ["mail.thread"]
    _order = "start_date desc, id desc"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Leave empty for an institution-wide round.",
    )
    start_date = fields.Date(string="Start Date", required=True, tracking=True)
    end_date = fields.Date(string="End Date", required=True, tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    capacity = fields.Integer(
        string="Total Seats",
        help="Optional overall seat cap for the round (0 = unlimited).",
    )
    allow_waitlist = fields.Boolean(string="Allow Waitlist", default=True)
    sequence_prefix = fields.Char(
        string="Application Prefix",
        help="Optional extra prefix added to application numbers of this round.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    applicant_ids = fields.One2many(
        comodel_name="univ.applicant",
        inverse_name="round_id",
        string="Applicants",
    )
    applicant_count = fields.Integer(
        string="Applicants", compute="_compute_applicant_count"
    )
    enrolled_count = fields.Integer(
        string="Enrolled", compute="_compute_applicant_count"
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The round code must be unique per campus.",
        ),
    ]

    @api.depends("applicant_ids", "applicant_ids.stage_id.is_won")
    def _compute_applicant_count(self):
        for record in self:
            applicants = record.applicant_ids
            record.applicant_count = len(applicants)
            record.enrolled_count = len(
                applicants.filtered(lambda a: a.stage_id.is_won)
            )

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.end_date < record.start_date:
                raise ValidationError(
                    self.env._("Round end date cannot precede the start date.")
                )

    def action_open(self):
        self.write({"state": "open"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_view_applicants(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Applicants"),
            "res_model": "univ.applicant",
            "view_mode": "list,kanban,form",
            "domain": [("round_id", "=", self.id)],
            "context": {"default_round_id": self.id},
        }
