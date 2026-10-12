# -*- coding: utf-8 -*-
import hashlib

from odoo import api, fields, models


class UnivResultTranscript(models.Model):
    _name = "univ.result.transcript"
    _description = "Academic Transcript"
    _inherit = ["mail.thread"]
    _order = "student_id, version desc"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student", required=True,
        ondelete="cascade", index=True, tracking=True,
    )
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program",
        related="student_id.program_id", store=True,
    )
    semester_result_ids = fields.Many2many(
        comodel_name="univ.result.semester", string="Semester Results",
    )
    total_credits = fields.Float(string="Total Credits", compute="_compute_cgpa",
                                 store=True)
    cgpa = fields.Float(string="CGPA", compute="_compute_cgpa", store=True,
                        tracking=True)
    generated_on = fields.Datetime(string="Generated On")
    version = fields.Integer(string="Version", default=1)
    integrity_hash = fields.Char(string="Integrity Hash", readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="student_id.company_id", store=True, index=True,
    )

    @api.depends("student_id", "version")
    def _compute_name(self):
        for record in self:
            record.name = "Transcript - %s v%s" % (
                record.student_id.display_name or "", record.version,
            )

    @api.depends("semester_result_ids.sgpa", "semester_result_ids.total_credits")
    def _compute_cgpa(self):
        for record in self:
            credits = sum(record.semester_result_ids.mapped("total_credits"))
            weighted = sum(
                r.sgpa * r.total_credits for r in record.semester_result_ids
            )
            record.total_credits = credits
            record.cgpa = (weighted / credits) if credits else 0.0

    def action_generate(self):
        """Roll up every published semester result for the student."""
        for record in self:
            results = self.env["univ.result.semester"].search([
                ("student_id", "=", record.student_id.id),
                ("published", "=", True),
            ])
            record.semester_result_ids = [(6, 0, results.ids)]
            record.generated_on = fields.Datetime.now()
            record._compute_cgpa()
            payload = "%s|%s|%.4f|%s" % (
                record.student_id.id, record.version, record.cgpa,
                ",".join(str(r.id) for r in results),
            )
            record.integrity_hash = hashlib.sha256(
                payload.encode("utf-8")
            ).hexdigest()
        return True

    def action_new_version(self):
        self.ensure_one()
        copy = self.copy({"version": self.version + 1})
        copy.action_generate()
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.result.transcript",
            "res_id": copy.id,
            "view_mode": "form",
            "target": "current",
        }
