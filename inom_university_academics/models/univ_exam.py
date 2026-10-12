# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivExam(models.Model):
    _name = "univ.exam"
    _description = "Examination"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Exam", required=True, tracking=True)
    code = fields.Char(string="Code", copy=False)
    exam_type_id = fields.Many2one(
        comodel_name="univ.exam.type", string="Exam Type", required=True,
        tracking=True,
    )
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program", required=True,
        ondelete="restrict", index=True, tracking=True,
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester", string="Semester", required=True,
        ondelete="restrict", index=True, tracking=True,
    )
    academic_year_id = fields.Many2one(
        comodel_name="univ.academic.session", string="Academic Year",
    )
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    state = fields.Selection(
        selection=[
            ("draft", "Draft Schedule"),
            ("published", "Published"),
            ("allocated", "Halls & Invigilators"),
            ("tickets", "Hall Tickets Issued"),
            ("conducted", "Conducted"),
            ("marks", "Marks Entry"),
            ("moderation", "HOD Moderation"),
            ("coe", "CoE Approval"),
            ("result", "Result Published"),
        ],
        string="Status", default="draft", required=True, tracking=True,
    )
    schedule_ids = fields.One2many(
        comodel_name="univ.exam.schedule", inverse_name="exam_id",
        string="Schedule",
    )
    schedule_count = fields.Integer(compute="_compute_counts", string="Subjects")
    grade_scale_id = fields.Many2one(
        comodel_name="univ.grade.scale", string="Grade Scale",
        default=lambda self: self.env["univ.grade.scale"]._get_default(),
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", required=True,
        default=lambda self: self.env.company, index=True,
    )

    def _compute_counts(self):
        for exam in self:
            exam.schedule_count = len(exam.schedule_ids)

    def action_publish(self):
        for exam in self:
            if not exam.schedule_ids:
                raise UserError(self.env._("Add at least one subject schedule."))
            exam.state = "published"

    def action_mark_allocated(self):
        self.write({"state": "allocated"})

    def action_issue_hall_tickets(self):
        self.write({"state": "tickets"})

    def action_conducted(self):
        self.write({"state": "conducted"})

    def action_open_marks(self):
        self.write({"state": "marks"})

    def action_send_moderation(self):
        self.write({"state": "moderation"})

    def action_coe_approval(self):
        for exam in self:
            if not self.env.user.has_group(
                "inom_university_academics.group_univ_controller_examinations"
            ):
                raise UserError(self.env._(
                    "Only the Controller of Examinations can approve results."
                ))
            exam.state = "coe"

    def action_publish_result(self):
        for exam in self:
            if exam.state != "coe":
                raise UserError(self.env._(
                    "Results require CoE approval before publication."
                ))
            exam.state = "result"

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_view_schedules(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Exam Schedule"),
            "res_model": "univ.exam.schedule",
            "view_mode": "list,form",
            "domain": [("exam_id", "=", self.id)],
            "context": {"default_exam_id": self.id},
        }
