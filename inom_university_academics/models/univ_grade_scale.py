# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivGradeScale(models.Model):
    _name = "univ.grade.scale"
    _description = "Grade Scale"
    _order = "name"

    name = fields.Char(string="Grade Scale", required=True)
    is_default = fields.Boolean(string="Default")
    pass_grade_point = fields.Float(
        string="Minimum Pass Grade Point", default=4.0,
        help="A subject grade point at or above this value is a pass.",
    )
    line_ids = fields.One2many(
        comodel_name="univ.grade.scale.line", inverse_name="scale_id",
        string="Grades",
    )
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True,
    )

    @api.model
    def _get_default(self):
        scale = self.search([("is_default", "=", True)], limit=1)
        if not scale:
            scale = self.search([], limit=1)
        return scale

    def grade_for_percent(self, percent):
        """Return (grade_label, grade_point, is_pass) for a percentage."""
        self.ensure_one()
        for line in self.line_ids.sorted("min_percent", reverse=True):
            if percent >= line.min_percent:
                return (line.name, line.grade_point,
                        line.grade_point >= self.pass_grade_point)
        return ("F", 0.0, False)


class UnivGradeScaleLine(models.Model):
    _name = "univ.grade.scale.line"
    _description = "Grade Scale Line"
    _order = "min_percent desc"

    scale_id = fields.Many2one(
        comodel_name="univ.grade.scale", string="Scale", required=True,
        ondelete="cascade", index=True,
    )
    name = fields.Char(string="Grade", required=True)
    min_percent = fields.Float(string="Minimum %", required=True)
    grade_point = fields.Float(string="Grade Point", required=True)
