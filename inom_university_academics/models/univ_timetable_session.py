# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivTimetableSession(models.Model):
    _name = "univ.timetable.session"
    _description = "Timetable Session"
    _inherit = ["mail.thread"]
    _order = "date, slot_id"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    section_id = fields.Many2one(
        comodel_name="univ.section", string="Section", required=True,
        ondelete="cascade", index=True, tracking=True,
    )
    subject_id = fields.Many2one(
        comodel_name="univ.subject", string="Subject", required=True,
        ondelete="restrict", index=True, tracking=True,
    )
    faculty_id = fields.Many2one(
        comodel_name="univ.faculty", string="Faculty", required=True,
        ondelete="restrict", index=True, tracking=True,
    )
    room_id = fields.Many2one(
        comodel_name="univ.room", string="Room", ondelete="restrict", index=True,
    )
    slot_id = fields.Many2one(
        comodel_name="univ.timeslot", string="Time Slot", required=True,
        ondelete="restrict", index=True,
    )
    date = fields.Date(string="Date", required=True, index=True)
    weekday = fields.Selection(
        selection=[
            ("0", "Monday"), ("1", "Tuesday"), ("2", "Wednesday"),
            ("3", "Thursday"), ("4", "Friday"), ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Weekday", compute="_compute_weekday", store=True,
    )
    program_id = fields.Many2one(
        comodel_name="univ.program", string="Program",
        related="section_id.program_id", store=True,
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester", string="Semester",
        related="section_id.semester_id", store=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("confirmed", "Confirmed"),
                   ("cancelled", "Cancelled")],
        string="Status", default="draft", required=True, tracking=True,
    )
    is_substituted = fields.Boolean(string="Substituted", default=False)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="section_id.company_id", store=True, index=True,
    )

    @api.depends("date")
    def _compute_weekday(self):
        for record in self:
            record.weekday = str(record.date.weekday()) if record.date else False

    @api.depends("section_id", "subject_id", "slot_id", "date")
    def _compute_name(self):
        for record in self:
            record.name = " / ".join(
                p for p in [
                    record.section_id.display_name,
                    record.subject_id.code or record.subject_id.display_name,
                    record.slot_id.name,
                ] if p
            )

    @api.constrains("faculty_id", "room_id", "section_id", "slot_id", "date", "state")
    def _check_clash(self):
        """Hard constraint: same faculty / room / section cannot be double-booked
        in the same slot on the same date among active (non-cancelled) sessions."""
        for record in self:
            if record.state == "cancelled":
                continue
            base = [
                ("id", "!=", record.id),
                ("date", "=", record.date),
                ("slot_id", "=", record.slot_id.id),
                ("state", "!=", "cancelled"),
            ]
            if self.search_count(base + [("faculty_id", "=", record.faculty_id.id)]):
                raise ValidationError(_(
                    "Clash: faculty %(f)s is already booked in this slot on %(d)s.",
                    f=record.faculty_id.display_name, d=record.date,
                ))
            if record.room_id and self.search_count(
                    base + [("room_id", "=", record.room_id.id)]):
                raise ValidationError(_(
                    "Clash: room %(r)s is already booked in this slot on %(d)s.",
                    r=record.room_id.display_name, d=record.date,
                ))
            if self.search_count(base + [("section_id", "=", record.section_id.id)]):
                raise ValidationError(_(
                    "Clash: section %(s)s already has a session in this slot on %(d)s.",
                    s=record.section_id.display_name, d=record.date,
                ))

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_open_attendance(self):
        """Open (creating if needed) the attendance sheet for this session."""
        self.ensure_one()
        sheet = self.env["univ.attendance.sheet"].search(
            [("session_id", "=", self.id)], limit=1
        )
        if not sheet:
            sheet = self.env["univ.attendance.sheet"].create({"session_id": self.id})
            sheet.action_generate_lines()
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.attendance.sheet",
            "res_id": sheet.id,
            "view_mode": "form",
            "target": "current",
        }
