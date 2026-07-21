# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivStudentGuardian(models.Model):
    _name = "univ.student.guardian"
    _description = "Student Guardian"
    _order = "is_primary desc, name"

    name = fields.Char(string="Name", required=True)
    student_id = fields.Many2one(
        comodel_name="univ.student",
        string="Student",
        required=True,
        ondelete="cascade",
        index=True,
    )
    relationship = fields.Selection(
        selection=[
            ("father", "Father"),
            ("mother", "Mother"),
            ("guardian", "Guardian"),
            ("sibling", "Sibling"),
            ("spouse", "Spouse"),
            ("other", "Other"),
        ],
        string="Relationship",
        default="father",
        required=True,
    )
    is_primary = fields.Boolean(string="Primary Guardian", default=False)
    phone = fields.Char(string="Phone")
    mobile = fields.Char(string="Mobile")
    email = fields.Char(string="Email")
    occupation = fields.Char(string="Occupation")
    address = fields.Text(string="Address")
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Related Contact",
        ondelete="set null",
        help="Link to a portal contact to grant the parent portal access.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="student_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    @api.constrains("is_primary", "student_id")
    def _check_single_primary(self):
        for record in self.filtered("is_primary"):
            others = self.search_count(
                [
                    ("student_id", "=", record.student_id.id),
                    ("is_primary", "=", True),
                    ("id", "!=", record.id),
                ]
            )
            if others:
                raise ValidationError(
                    _(
                        "A student may have only one primary guardian."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        guardians = super().create(vals_list)
        guardians.filtered("partner_id").partner_id.write(
            {"is_univ_guardian": True}
        )
        return guardians
