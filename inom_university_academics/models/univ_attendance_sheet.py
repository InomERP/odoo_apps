# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivAttendanceSheet(models.Model):
    _name = "univ.attendance.sheet"
    _description = "Attendance Sheet"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    session_id = fields.Many2one(
        comodel_name="univ.timetable.session", string="Session", required=True,
        ondelete="cascade", index=True, tracking=True,
    )
    section_id = fields.Many2one(
        comodel_name="univ.section", string="Section",
        related="session_id.section_id", store=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject",
        related="session_id.subject_id", store=True, index=True,
    )
    faculty_id = fields.Many2one(
        comodel_name="univ.faculty", string="Faculty",
        related="session_id.faculty_id", store=True, index=True,
    )
    date = fields.Date(string="Date", related="session_id.date", store=True, index=True)
    slot_id = fields.Many2one(
        comodel_name="univ.timeslot", string="Slot",
        related="session_id.slot_id", store=True,
    )
    marked_by = fields.Many2one(comodel_name="res.users", string="Marked By",
                                readonly=True)
    submitted_on = fields.Datetime(string="Submitted On", readonly=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("open", "Marking Open"),
            ("submitted", "Submitted"),
            ("locked", "Locked"),
        ],
        string="Status", default="draft", required=True, tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="univ.attendance.line", inverse_name="sheet_id",
        string="Lines",
    )
    present_count = fields.Integer(string="Present", compute="_compute_counts",
                                   store=True)
    absent_count = fields.Integer(string="Absent", compute="_compute_counts",
                                  store=True)
    total_count = fields.Integer(string="Total", compute="_compute_counts",
                                 store=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="session_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("session_uniq", "unique(session_id)",
         "An attendance sheet already exists for this session."),
    ]

    @api.depends("session_id")
    def _compute_name(self):
        for record in self:
            record.name = record.session_id.name or self.env._("Attendance")

    @api.depends("line_ids.state")
    def _compute_counts(self):
        for record in self:
            lines = record.line_ids
            record.total_count = len(lines)
            record.present_count = len(
                lines.filtered(lambda l: l.state in ("present", "late"))
            )
            record.absent_count = len(
                lines.filtered(lambda l: l.state == "absent")
            )

    def action_generate_lines(self):
        """Populate one line per student in the session's section."""
        for record in self:
            existing = record.line_ids.mapped("student_id")
            students = record.section_id.student_ids.filtered(
                lambda s: s.state == "active"
            )
            vals = [
                (0, 0, {"student_id": student.id})
                for student in students if student not in existing
            ]
            if vals:
                record.line_ids = vals
            if record.state == "draft":
                record.state = "open"
        return True

    def action_mark_all_present(self):
        for record in self:
            record._ensure_editable()
            record.line_ids.filtered(lambda l: l.state == "absent").write(
                {"state": "present"}
            )

    def action_submit(self):
        for record in self:
            if record.state not in ("draft", "open"):
                raise UserError(self.env._("Sheet is already submitted or locked."))
            if not record.line_ids:
                raise UserError(self.env._("Generate the student list first."))
            record.write({
                "state": "submitted",
                "marked_by": self.env.user.id,
                "submitted_on": fields.Datetime.now(),
            })
            record._notify_absentees()

    def action_lock(self):
        self.write({"state": "locked"})

    def action_request_unlock(self):
        """Post-lock edits require HOD approval; reopens marking and audit-logs."""
        for record in self:
            if record.state != "locked":
                raise UserError(self.env._("Only locked sheets can be reopened."))
            if not self.env.user.has_group("inom_university_core.group_univ_hod") \
                    and not self.env.user.has_group(
                        "inom_university_academics.group_univ_academic_admin"):
                raise UserError(self.env._(
                    "Only an HOD or Academic Admin can reopen a locked sheet."
                ))
            record.state = "open"
            record.message_post(body=self.env._(
                "Locked sheet reopened for correction by %s.",
                self.env.user.display_name,
            ))

    def _ensure_editable(self):
        self.ensure_one()
        if self.state == "locked":
            raise UserError(self.env._(
                "This sheet is locked. Request an HOD reopen to edit."
            ))

    def _notify_absentees(self):
        """Template-driven absence notification (email; SMS is a pluggable hook)."""
        self.ensure_one()
        template = self.env.ref(
            "inom_university_academics.email_template_absence_alert",
            raise_if_not_found=False,
        )
        if not template:
            return
        for line in self.line_ids.filtered(lambda l: l.state == "absent"):
            if line.student_id.partner_id.email:
                template.send_mail(line.id, force_send=False)

    @api.model
    def _cron_lock_sheets(self):
        """Auto-lock sheets submitted more than 24h ago."""
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        sheets = self.search([
            ("state", "=", "submitted"),
            ("submitted_on", "<", cutoff),
        ])
        sheets.write({"state": "locked"})


class UnivAttendanceLine(models.Model):
    _name = "univ.attendance.line"
    _description = "Attendance Line"
    _inherit = ["univ.audit.mixin"]
    _order = "sheet_id, student_id"

    _audit_log_fields = ["state"]

    sheet_id = fields.Many2one(
        comodel_name="univ.attendance.sheet", string="Sheet", required=True,
        ondelete="cascade", index=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student", string="Student", required=True,
        ondelete="restrict", index=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject",
        related="sheet_id.subject_id", store=True, index=True,
    )
    date = fields.Date(string="Date", related="sheet_id.date", store=True, index=True)
    state = fields.Selection(
        selection=[
            ("present", "Present"),
            ("absent", "Absent"),
            ("late", "Late"),
            ("leave", "On Leave"),
        ],
        string="Status", default="absent", required=True,
    )
    remark = fields.Char(string="Remark")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="sheet_id.company_id", store=True, index=True,
    )

    _sql_constraints = [
        ("sheet_student_uniq", "unique(sheet_id, student_id)",
         "A student appears only once per attendance sheet."),
    ]

    def write(self, vals):
        if "state" in vals:
            for line in self:
                if line.sheet_id.state == "locked":
                    raise UserError(self.env._(
                        "Cannot edit a locked attendance sheet."
                    ))
        return super().write(vals)
