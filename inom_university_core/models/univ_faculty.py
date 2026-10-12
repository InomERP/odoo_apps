# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivFaculty(models.Model):
    _name = "univ.faculty"
    _description = "Faculty / Staff"
    _inherit = ["univ.audit.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "name"

    # Fields whose changes are written to the immutable audit log.
    _audit_log_fields = ["department_id", "designation", "active"]

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(
        string="Faculty Code", readonly=True, copy=False, index=True, tracking=True
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Related Contact",
        ondelete="restrict",
        copy=False,
    )
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
    designation = fields.Selection(
        selection=[
            ("professor", "Professor"),
            ("associate_professor", "Associate Professor"),
            ("assistant_professor", "Assistant Professor"),
            ("lecturer", "Lecturer"),
            ("lab_assistant", "Lab Assistant"),
            ("visiting", "Visiting Faculty"),
            ("other", "Other"),
        ],
        string="Designation",
        default="assistant_professor",
        required=True,
        tracking=True,
    )
    faculty_type = fields.Selection(
        selection=[
            ("teaching", "Teaching"),
            ("non_teaching", "Non-Teaching"),
        ],
        string="Staff Type",
        default="teaching",
        required=True,
    )
    qualification = fields.Char(string="Qualifications")
    experience_years = fields.Float(string="Experience (Years)")
    joining_date = fields.Date(string="Joining Date")
    gender = fields.Selection(
        selection=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        string="Gender",
    )
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile")
    image_1920 = fields.Image(string="Photo")
    active = fields.Boolean(string="Active", default=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    subject_ids = fields.Many2many(
        comodel_name="univ.subject",
        relation="univ_subject_faculty_rel",
        column1="faculty_id",
        column2="subject_id",
        string="Subjects",
    )
    subject_count = fields.Integer(
        string="Subjects", compute="_compute_subject_count"
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The faculty code must be unique per campus.",
        ),
    ]

    @api.depends("subject_ids")
    def _compute_subject_count(self):
        for record in self:
            record.subject_count = len(record.subject_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                company = self.env["res.company"].browse(
                    vals.get("company_id")
                ) or self.env.company
                prefix = company.univ_faculty_prefix or "FAC"
                sequence = self.env["ir.sequence"].next_by_code(
                    "univ.faculty.code"
                ) or "0001"
                vals["code"] = "%s/%s" % (prefix, sequence)
            if not vals.get("partner_id") and vals.get("name"):
                partner = self.env["res.partner"].create(
                    {
                        "name": vals["name"],
                        "is_univ_faculty": True,
                        "email": vals.get("email"),
                        "phone": vals.get("phone"),
                        "company_id": vals.get("company_id"),
                    }
                )
                vals["partner_id"] = partner.id
        return super().create(vals_list)

    def action_view_subjects(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Subjects"),
            "res_model": "univ.subject",
            "view_mode": "list,form",
            "domain": [("id", "in", self.subject_ids.ids)],
        }
