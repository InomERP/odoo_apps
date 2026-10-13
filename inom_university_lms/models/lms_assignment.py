# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class UnivAssignment(models.Model):
    _name = "univ.assignment"
    _description = "Assignment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "due_date desc, id desc"

    name = fields.Char(string="Title", required=True, tracking=True)
    subject_id = fields.Many2one(comodel_name="univ.subject", string="Subject",
                                 required=True, index=True)
    faculty_id = fields.Many2one(comodel_name="univ.faculty", string="Faculty")
    instructions = fields.Html(string="Instructions")
    assigned_date = fields.Date(string="Assigned On",
                                default=fields.Date.context_today)
    due_date = fields.Datetime(string="Due Date", required=True, tracking=True)
    max_marks = fields.Float(string="Maximum Marks", default=100.0)
    allow_late = fields.Boolean(string="Allow Late Submission", default=True)
    attachment_ids = fields.Many2many(comodel_name="ir.attachment",
                                      string="Attachments")
    submission_ids = fields.One2many(
        comodel_name="univ.assignment.submission",
        inverse_name="assignment_id", string="Submissions")
    submission_count = fields.Integer(string="Submissions",
                                      compute="_compute_stats")
    graded_count = fields.Integer(string="Graded", compute="_compute_stats")
    state = fields.Selection(
        selection=[("draft", "Draft"), ("published", "Published"),
                   ("closed", "Closed")],
        string="Status", default="draft", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    @api.depends("submission_ids.state")
    def _compute_stats(self):
        for rec in self:
            rec.submission_count = len(rec.submission_ids)
            rec.graded_count = len(rec.submission_ids.filtered(
                lambda s: s.state == "graded"))

    def action_publish(self):
        self.write({"state": "published"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_view_submissions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Submissions"),
            "res_model": "univ.assignment.submission",
            "view_mode": "list,form",
            "domain": [("assignment_id", "=", self.id)],
            "context": {"default_assignment_id": self.id},
        }


class UnivAssignmentSubmission(models.Model):
    _name = "univ.assignment.submission"
    _description = "Assignment Submission"
    _inherit = ["mail.thread"]
    _order = "submitted_on desc, id desc"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    assignment_id = fields.Many2one(comodel_name="univ.assignment",
                                    string="Assignment", required=True,
                                    ondelete="cascade", index=True)
    subject_id = fields.Many2one(comodel_name="univ.subject", string="Subject",
                                 related="assignment_id.subject_id", store=True)
    student_id = fields.Many2one(comodel_name="univ.student", string="Student",
                                 required=True, index=True)
    submitted_on = fields.Datetime(string="Submitted On",
                                   default=fields.Datetime.now)
    is_late = fields.Boolean(string="Late", compute="_compute_late", store=True)
    attachment_ids = fields.Many2many(comodel_name="ir.attachment",
                                      string="Files")
    note = fields.Text(string="Student Note")
    grade = fields.Float(string="Grade")
    max_marks = fields.Float(string="Out Of", related="assignment_id.max_marks")
    feedback = fields.Text(string="Feedback")
    state = fields.Selection(
        selection=[("submitted", "Submitted"), ("graded", "Graded")],
        string="Status", default="submitted", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    _sql_constraints = [
        ("assignment_student_uniq", "unique(assignment_id, student_id)",
         "A student can submit an assignment only once."),
    ]

    @api.depends("assignment_id", "student_id")
    def _compute_name(self):
        for rec in self:
            rec.name = "%s / %s" % (rec.assignment_id.name or "",
                                    rec.student_id.display_name or "")

    @api.depends("submitted_on", "assignment_id.due_date")
    def _compute_late(self):
        for rec in self:
            due = rec.assignment_id.due_date
            rec.is_late = bool(due and rec.submitted_on and rec.submitted_on > due)

    @api.constrains("assignment_id", "is_late")
    def _check_late_allowed(self):
        for rec in self:
            if rec.is_late and not rec.assignment_id.allow_late:
                raise ValidationError(self.env._(
                    "Late submission is not allowed for this assignment."))

    @api.constrains("grade")
    def _check_grade(self):
        for rec in self:
            if rec.grade < 0 or rec.grade > rec.max_marks:
                raise ValidationError(self.env._(
                    "Grade must be between 0 and %s.", rec.max_marks))

    def action_grade(self):
        for rec in self:
            rec.state = "graded"
