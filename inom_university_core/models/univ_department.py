# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivDepartment(models.Model):
    _name = "univ.department"
    _description = "Department"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "complete_name, name"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)
    complete_name = fields.Char(
        string="Full Name", compute="_compute_complete_name", store=True
    )
    faculty_school_id = fields.Many2one(
        comodel_name="univ.faculty_school",
        string="Faculty / School",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    hod_faculty_id = fields.Many2one(
        comodel_name="univ.faculty",
        string="Head of Department",
        tracking=True,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="faculty_school_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    program_ids = fields.One2many(
        comodel_name="univ.program",
        inverse_name="department_id",
        string="Programs",
    )
    program_count = fields.Integer(
        string="Programs", compute="_compute_program_count"
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The department code must be unique per campus.",
        ),
    ]

    @api.depends("name", "faculty_school_id.name")
    def _compute_complete_name(self):
        for record in self:
            if record.faculty_school_id:
                record.complete_name = "%s / %s" % (
                    record.faculty_school_id.name,
                    record.name or "",
                )
            else:
                record.complete_name = record.name or ""

    @api.depends("program_ids")
    def _compute_program_count(self):
        for record in self:
            record.program_count = len(record.program_ids)
