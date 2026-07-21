# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class UnivProgram(models.Model):
    _name = "univ.program"
    _description = "Program"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)
    department_id = fields.Many2one(
        comodel_name="univ.department",
        string="Department",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    faculty_school_id = fields.Many2one(
        comodel_name="univ.faculty_school",
        string="Faculty / School",
        related="department_id.faculty_school_id",
        store=True,
        readonly=True,
    )
    degree_type = fields.Selection(
        selection=[
            ("ug", "Undergraduate"),
            ("pg", "Postgraduate"),
            ("diploma", "Diploma"),
            ("phd", "Doctorate (PhD)"),
            ("certificate", "Certificate"),
        ],
        string="Degree Type",
        default="ug",
        required=True,
        tracking=True,
    )
    duration_years = fields.Float(
        string="Duration (Years)", default=4.0, tracking=True
    )
    total_semesters = fields.Integer(string="Total Semesters", default=8)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="department_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    batch_ids = fields.One2many(
        comodel_name="univ.batch", inverse_name="program_id", string="Batches"
    )
    semester_ids = fields.One2many(
        comodel_name="univ.semester", inverse_name="program_id", string="Semesters"
    )
    subject_ids = fields.One2many(
        comodel_name="univ.subject", inverse_name="program_id", string="Subjects"
    )
    student_ids = fields.One2many(
        comodel_name="univ.student", inverse_name="program_id", string="Students"
    )
    student_count = fields.Integer(
        string="Students", compute="_compute_student_count"
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The program code must be unique per campus.",
        ),
    ]

    @api.depends("student_ids")
    def _compute_student_count(self):
        for record in self:
            record.student_count = len(record.student_ids)

    def action_open_students(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Students"),
            "res_model": "univ.student",
            "view_mode": "list,form,kanban",
            "domain": [("program_id", "=", self.id)],
            "context": {"default_program_id": self.id},
        }
