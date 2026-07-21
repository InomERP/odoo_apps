# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivSubject(models.Model):
    _name = "univ.subject"
    _description = "Subject"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "program_id, code, name"

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
    semester_id = fields.Many2one(
        comodel_name="univ.semester",
        string="Semester",
        ondelete="set null",
        index=True,
    )
    credit_hours = fields.Float(string="Credit Hours", default=3.0, tracking=True)
    subject_type = fields.Selection(
        selection=[
            ("core", "Core"),
            ("elective", "Elective"),
            ("lab", "Laboratory"),
            ("project", "Project"),
        ],
        string="Subject Type",
        default="core",
        required=True,
        tracking=True,
    )
    elective_group_id = fields.Many2one(
        comodel_name="univ.subject.elective.group",
        string="Elective Group",
        ondelete="set null",
        index=True,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="program_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    faculty_ids = fields.Many2many(
        comodel_name="univ.faculty",
        relation="univ_subject_faculty_rel",
        column1="subject_id",
        column2="faculty_id",
        string="Faculty",
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The subject code must be unique per campus.",
        ),
        (
            "credit_hours_positive",
            "check(credit_hours >= 0)",
            "Credit hours cannot be negative.",
        ),
    ]

    @api.constrains("subject_type", "elective_group_id")
    def _check_elective_group(self):
        for record in self:
            if record.elective_group_id and record.subject_type != "elective":
                raise ValidationError(
                    _(
                        "Only elective subjects may belong to an elective group."
                    )
                )
