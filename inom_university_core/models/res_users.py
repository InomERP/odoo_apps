# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    univ_department_ids = fields.Many2many(
        comodel_name="univ.department",
        string="University Departments",
        compute="_compute_univ_department_ids",
        help="Departments tied to this user, used by department-scoped record "
        "rules: the department of the user's faculty record plus any "
        "department the user heads.",
    )

    def _compute_univ_department_ids(self):
        Faculty = self.env["univ.faculty"].sudo()
        Department = self.env["univ.department"].sudo()
        for user in self:
            faculty = Faculty.search(
                [("partner_id", "=", user.partner_id.id)], limit=1
            )
            departments = faculty.department_id
            if faculty:
                departments |= Department.search(
                    [("hod_faculty_id", "=", faculty.id)]
                )
            user.univ_department_ids = departments
