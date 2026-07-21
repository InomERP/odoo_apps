# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class UnivFacultySchool(models.Model):
    _name = "univ.faculty_school"
    _description = "Faculty / School"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)
    sequence = fields.Integer(string="Sequence", default=10)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    department_ids = fields.One2many(
        comodel_name="univ.department",
        inverse_name="faculty_school_id",
        string="Departments",
    )
    department_count = fields.Integer(
        string="Departments", compute="_compute_department_count"
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The faculty/school code must be unique per campus.",
        ),
    ]

    @api.depends("department_ids")
    def _compute_department_count(self):
        for record in self:
            record.department_count = len(record.department_ids)

    def action_open_departments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Departments"),
            "res_model": "univ.department",
            "view_mode": "list,form",
            "domain": [("faculty_school_id", "=", self.id)],
            "context": {"default_faculty_school_id": self.id},
        }
