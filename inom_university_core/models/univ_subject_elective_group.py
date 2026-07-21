# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivSubjectElectiveGroup(models.Model):
    _name = "univ.subject.elective.group"
    _description = "Subject Elective Group"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

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
    min_select = fields.Integer(string="Minimum to Select", default=1)
    max_select = fields.Integer(string="Maximum to Select", default=1)
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="program_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    subject_ids = fields.One2many(
        comodel_name="univ.subject",
        inverse_name="elective_group_id",
        string="Subjects",
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The elective group code must be unique per campus.",
        ),
    ]

    @api.constrains("min_select", "max_select")
    def _check_selection_bounds(self):
        for record in self:
            if record.min_select < 0 or record.max_select < 0:
                raise ValidationError(
                    _("Selection bounds cannot be negative.")
                )
            if record.max_select and record.min_select > record.max_select:
                raise ValidationError(
                    _(
                        "Minimum to select cannot exceed maximum to select."
                    )
                )
