# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UnivSection(models.Model):
    _name = "univ.section"
    _description = "Section"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "batch_id, semester_id, name"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)
    batch_id = fields.Many2one(
        comodel_name="univ.batch",
        string="Batch",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester",
        string="Semester",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        related="batch_id.program_id",
        store=True,
        readonly=True,
    )
    capacity = fields.Integer(string="Capacity", default=60)
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="batch_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    student_ids = fields.One2many(
        comodel_name="univ.student", inverse_name="section_id", string="Students"
    )
    student_count = fields.Integer(
        string="Students", compute="_compute_student_count"
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The section code must be unique per campus.",
        ),
    ]

    @api.depends("student_ids")
    def _compute_student_count(self):
        for record in self:
            record.student_count = len(record.student_ids)

    @api.constrains("capacity")
    def _check_capacity(self):
        for record in self:
            if record.capacity < 0:
                raise ValidationError(
                    self.env._("Section capacity cannot be negative.")
                )
