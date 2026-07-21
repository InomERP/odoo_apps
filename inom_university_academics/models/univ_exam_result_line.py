# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UnivExamResultLine(models.Model):
    _name = "univ.exam.result.line"
    _description = "Exam Result Line"
    _inherit = ["univ.audit.mixin"]
    _order = "schedule_id, student_id"

    _audit_log_fields = ["obtained", "second_obtained", "moderated", "state"]

    schedule_id = fields.Many2one(
        comodel_name="univ.exam.schedule", string="Exam Schedule", required=True,
        ondelete="cascade", index=True,
    )
    exam_id = fields.Many2one(
        comodel_name="univ.exam", string="Exam",
        related="schedule_id.exam_id", store=True, index=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student", required=True,
        ondelete="restrict", index=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject",
        related="schedule_id.subject_id", store=True, index=True,
    )
    max_marks = fields.Float(string="Max Marks", required=True, default=100.0)
    obtained = fields.Float(string="Marks (Evaluator 1)")
    second_obtained = fields.Float(string="Marks (Evaluator 2)",
                                   help="Optional double-blind second evaluation.")
    moderated = fields.Float(string="Moderated Marks")
    final_marks = fields.Float(string="Final Marks", compute="_compute_final",
                               store=True)
    percent = fields.Float(string="%", compute="_compute_final", store=True)
    grade = fields.Char(string="Grade", compute="_compute_grade", store=True)
    grade_point = fields.Float(string="Grade Point", compute="_compute_grade",
                               store=True)
    is_pass = fields.Boolean(string="Pass", compute="_compute_grade", store=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("entered", "Entered"),
            ("moderated", "Moderated"),
            ("approved", "Approved"),
        ],
        string="Status", default="draft", required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="schedule_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("schedule_student_uniq", "unique(schedule_id, student_id)",
         "One mark line per student per subject."),
    ]

    @api.constrains("obtained", "second_obtained", "moderated", "max_marks")
    def _check_range(self):
        for record in self:
            for value in (record.obtained, record.second_obtained,
                          record.moderated):
                if value < 0 or value > record.max_marks:
                    raise ValidationError(_(
                        "Marks must be between 0 and %(m)s.", m=record.max_marks,
                    ))

    @api.depends("obtained", "second_obtained", "moderated", "max_marks", "state")
    def _compute_final(self):
        for record in self:
            if record.moderated:
                final = record.moderated
            elif record.second_obtained:
                # Double-blind: average the two evaluations.
                final = (record.obtained + record.second_obtained) / 2.0
            else:
                final = record.obtained
            record.final_marks = final
            record.percent = (final / record.max_marks * 100.0) \
                if record.max_marks else 0.0

    @api.depends("percent", "exam_id.grade_scale_id")
    def _compute_grade(self):
        for record in self:
            scale = record.exam_id.grade_scale_id \
                or self.env["univ.grade.scale"]._get_default()
            if scale:
                grade, point, is_pass = scale.grade_for_percent(record.percent)
            else:
                grade, point, is_pass = ("-", 0.0, record.percent >= 40)
            record.grade = grade
            record.grade_point = point
            record.is_pass = is_pass

    def write(self, vals):
        # Once the parent exam result is published, lines are immutable; a
        # correction must go through re-evaluation (new version).
        locked_fields = {"obtained", "second_obtained", "moderated"}
        if locked_fields & set(vals) and not self.env.context.get("reevaluation"):
            for record in self:
                if record.exam_id.state == "result":
                    raise UserError(_(
                        "Published results are locked. Use re-evaluation to "
                        "create a revised version."
                    ))
        return super().write(vals)

    def action_set_entered(self):
        self.write({"state": "entered"})

    def action_set_moderated(self):
        self.write({"state": "moderated"})

    def action_set_approved(self):
        self.write({"state": "approved"})

    def action_request_reevaluation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Re-evaluation"),
            "res_model": "univ.reevaluation.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_result_line_id": self.id},
        }
