# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivExamReevaluation(models.Model):
    _name = "univ.exam.reevaluation"
    _description = "Exam Re-evaluation"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", copy=False, readonly=True,
                       default=lambda self: self.env._("New"))
    result_line_id = fields.Many2one(
        comodel_name="univ.exam.result.line", string="Result Line", required=True,
        ondelete="restrict", index=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student",
        related="result_line_id.student_id", store=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject",
        related="result_line_id.subject_id", store=True,
    )
    max_marks = fields.Float(string="Max Marks", related="result_line_id.max_marks")
    original_marks = fields.Float(string="Original Marks",
                                  related="result_line_id.final_marks", store=True)
    fee_paid = fields.Boolean(string="Re-evaluation Fee Paid")
    evaluator2_marks = fields.Float(string="Second Evaluator Marks")
    evaluator3_marks = fields.Float(string="Third Evaluator Marks")
    needs_third = fields.Boolean(string="Third Evaluation Required",
                                 compute="_compute_needs_third", store=True)
    revised_marks = fields.Float(string="Revised (best-of)",
                                 compute="_compute_revised", store=True)
    state = fields.Selection(
        selection=[
            ("draft", "Applied"),
            ("review", "Under Review"),
            ("done", "Completed"),
            ("refused", "Refused"),
        ],
        string="Status", default="draft", required=True, tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="result_line_id.company_id", store=True, index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] in (self.env._("New"), "New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "univ.exam.reevaluation"
                ) or "REEVAL/0001"
        return super().create(vals_list)

    @api.depends("original_marks", "evaluator2_marks", "max_marks")
    def _compute_needs_third(self):
        """A third evaluation is forced when evaluator-2 differs from the
        original by more than 10% of the maximum marks."""
        for record in self:
            if record.max_marks and record.evaluator2_marks:
                diff = abs(record.evaluator2_marks - record.original_marks)
                record.needs_third = diff > (record.max_marks * 0.10)
            else:
                record.needs_third = False

    @api.depends("original_marks", "evaluator2_marks", "evaluator3_marks",
                 "needs_third")
    def _compute_revised(self):
        for record in self:
            marks = [record.original_marks, record.evaluator2_marks]
            if record.needs_third:
                marks.append(record.evaluator3_marks)
            record.revised_marks = max(m for m in marks if m is not None)

    def action_review(self):
        self.write({"state": "review"})

    def action_refuse(self):
        self.write({"state": "refused"})

    def action_apply_revised(self):
        """Publish a revised result version: archive current marks and write the
        best-of result, then mark the parent exam result as a new version."""
        for record in self:
            if not record.fee_paid:
                raise UserError(self.env._(
                    "Re-evaluation fee must be paid before applying."
                ))
            if record.needs_third and not record.evaluator3_marks:
                raise UserError(self.env._(
                    "A third evaluation is required (difference exceeds 10%)."
                ))
            line = record.result_line_id
            line.message_post(body=self.env._(
                "Re-evaluation %(ref)s: marks revised from %(old)s to %(new)s.",
                ref=record.name, old=line.final_marks, new=record.revised_marks,
            ))
            # Write through the moderated field (bypasses the published lock via
            # the dedicated re-evaluation path).
            line.sudo().with_context(reevaluation=True).write(
                {"moderated": record.revised_marks}
            )
            # Bump the student's semester result version if present.
            sem = self.env["univ.result.semester"].search([
                ("student_id", "=", record.student_id.id),
                ("semester_id", "=", line.schedule_id.semester_id.id),
            ], limit=1)
            if sem:
                sem.action_recompute()
            record.state = "done"
