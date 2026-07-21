# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivBatch(models.Model):
    _name = "univ.batch"
    _description = "Batch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_year desc, name"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    start_year = fields.Integer(string="Start Year", required=True, tracking=True)
    end_year = fields.Integer(
        string="End Year", compute="_compute_end_year", store=True
    )
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="program_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    section_ids = fields.One2many(
        comodel_name="univ.section", inverse_name="batch_id", string="Sections"
    )
    student_ids = fields.One2many(
        comodel_name="univ.student", inverse_name="batch_id", string="Students"
    )
    student_count = fields.Integer(
        string="Students", compute="_compute_student_count"
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The batch code must be unique per campus.",
        ),
    ]

    @api.depends("start_year", "program_id.duration_years")
    def _compute_end_year(self):
        for record in self:
            duration = int(record.program_id.duration_years or 0)
            record.end_year = (record.start_year + duration) if record.start_year else 0

    @api.depends("student_ids")
    def _compute_student_count(self):
        for record in self:
            record.student_count = len(record.student_ids)

    @api.constrains("start_year")
    def _check_start_year(self):
        for record in self:
            if record.start_year and (record.start_year < 1900 or record.start_year > 2200):
                raise ValidationError(
                    _("Start year must be a realistic four-digit year.")
                )
