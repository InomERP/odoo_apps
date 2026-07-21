# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivSyllabus(models.Model):
    _name = "univ.syllabus"
    _description = "Subject Syllabus"
    _inherit = ["mail.thread"]
    _order = "subject_id, version desc"

    name = fields.Char(string="Title", compute="_compute_name", store=True)
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject", required=True,
        ondelete="restrict", index=True, tracking=True,
    )
    academic_year_id = fields.Many2one(
        comodel_name="univ.academic.session", string="Academic Year",
        required=True, index=True,
    )
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program",
        related="subject_id.program_id", store=True,
    )
    version = fields.Integer(string="Version", default=1, tracking=True)
    state = fields.Selection(
        selection=[("draft", "Draft"), ("approved", "Approved"),
                   ("archived", "Archived")],
        string="Status", default="draft", required=True, tracking=True,
    )
    total_hours = fields.Float(string="Total Hours", compute="_compute_total_hours",
                               store=True)
    unit_ids = fields.One2many(
        comodel_name="univ.syllabus.unit", inverse_name="syllabus_id",
        string="Units",
    )
    description = fields.Html(string="Overview")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="subject_id.company_id", store=True, index=True,
    )

    @api.depends("subject_id", "academic_year_id", "version")
    def _compute_name(self):
        for record in self:
            parts = [record.subject_id.display_name or ""]
            if record.academic_year_id:
                parts.append(record.academic_year_id.name)
            parts.append("v%s" % record.version)
            record.name = " - ".join(p for p in parts if p)

    @api.depends("unit_ids.hours")
    def _compute_total_hours(self):
        for record in self:
            record.total_hours = sum(record.unit_ids.mapped("hours"))

    def action_approve(self):
        self.write({"state": "approved"})

    def action_archive_version(self):
        self.write({"state": "archived"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_new_version(self):
        self.ensure_one()
        copy = self.copy({
            "version": self.version + 1,
            "state": "draft",
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.syllabus",
            "res_id": copy.id,
            "view_mode": "form",
            "target": "current",
        }


class UnivSyllabusUnit(models.Model):
    _name = "univ.syllabus.unit"
    _description = "Syllabus Unit"
    _order = "syllabus_id, sequence, id"

    syllabus_id = fields.Many2one(
        comodel_name="univ.syllabus", string="Syllabus", required=True,
        ondelete="cascade", index=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Unit / Chapter", required=True)
    hours = fields.Float(string="Hours", default=0.0)
    topics = fields.Text(string="Topics")
    lesson_plan_ids = fields.One2many(
        comodel_name="univ.lesson.plan", inverse_name="unit_id",
        string="Lesson Plans",
    )
