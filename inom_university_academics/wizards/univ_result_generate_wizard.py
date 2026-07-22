# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class UnivResultGenerateWizard(models.TransientModel):
    _name = "univ.result.generate.wizard"
    _description = "Generate Semester Results"

    program_id = fields.Many2one(comodel_name="univ.program", string="Program",
                                 required=True)
    semester_id = fields.Many2one(comodel_name="univ.semester", string="Semester",
                                  required=True)
    academic_year_id = fields.Many2one(
        comodel_name="univ.academic.session", string="Academic Year",
    )
    publish = fields.Boolean(string="Publish Immediately", default=False)

    def action_generate(self):
        """Compute credit-weighted SGPA per student for the semester."""
        self.ensure_one()
        students = self.env["univ.student"].search([
            ("program_id", "=", self.program_id.id),
            ("semester_id", "=", self.semester_id.id),
            ("state", "=", "active"),
        ])
        if not students:
            raise UserError(_("No active students in this semester."))
        Result = self.env["univ.result.semester"]
        results = Result
        for student in students:
            result = Result.search([
                ("student_id", "=", student.id),
                ("semester_id", "=", self.semester_id.id),
            ], limit=1)
            if not result:
                result = Result.create({
                    "student_id": student.id,
                    "semester_id": self.semester_id.id,
                    "academic_year_id": self.academic_year_id.id,
                })
            result.action_recompute()
            if self.publish:
                result.action_publish()
            results |= result
        return {
            "type": "ir.actions.act_window",
            "name": _("Semester Results"),
            "res_model": "univ.result.semester",
            "view_mode": "list,form",
            "domain": [("id", "in", results.ids)],
        }
