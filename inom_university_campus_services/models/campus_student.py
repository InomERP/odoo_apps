# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivStudent(models.Model):
    _inherit = "univ.student"

    library_open_count = fields.Integer(
        string="Books Issued", compute="_compute_campus_aggregates")
    hostel_room_label = fields.Char(
        string="Hostel Room", compute="_compute_campus_aggregates")
    transport_route_label = fields.Char(
        string="Transport Route", compute="_compute_campus_aggregates")
    pending_assignment_count = fields.Integer(
        string="Pending Assignments", compute="_compute_campus_aggregates")
    latest_sgpa = fields.Float(
        string="Latest SGPA", compute="_compute_campus_aggregates")

    def _compute_campus_aggregates(self):
        Issue = self.env["univ.library.issue"]
        Allot = self.env["univ.hostel.allotment"]
        Sub = self.env["univ.transport.subscription"]
        Assignment = self.env["univ.assignment"]
        Submission = self.env["univ.assignment.submission"]
        Result = self.env["univ.result.semester"]
        for student in self:
            student.library_open_count = Issue.search_count([
                ("member_id.student_id", "=", student.id),
                ("state", "in", ("issued", "overdue"))])

            allot = Allot.search([
                ("student_id", "=", student.id),
                ("state", "in", ("allotted", "checked_in"))], limit=1)
            student.hostel_room_label = (
                "%s / %s" % (allot.hostel_id.name, allot.room_id.name)
                if allot else False)

            sub = Sub.search([
                ("student_id", "=", student.id),
                ("state", "in", ("fee_added", "issued"))], limit=1)
            student.transport_route_label = sub.route_id.name if sub else False

            program_subjects = student.program_id.subject_ids.ids \
                if student.program_id else []
            published = Assignment.search([
                ("state", "=", "published"),
                ("subject_id", "in", program_subjects)]) if program_subjects \
                else Assignment.browse()
            submitted_ids = Submission.search([
                ("student_id", "=", student.id),
                ("assignment_id", "in", published.ids)]).mapped("assignment_id").ids
            student.pending_assignment_count = len(
                [a for a in published.ids if a not in submitted_ids])

            result = Result.search([
                ("student_id", "=", student.id), ("published", "=", True)],
                order="semester_id desc", limit=1)
            student.latest_sgpa = result.sgpa if result else 0.0

    def get_campus_dashboard(self):
        """Return a dict of all dashboard-card values for the portal."""
        self.ensure_one()
        Exam = self.env["univ.exam.schedule"]
        upcoming = Exam.search([
            ("program_id", "=", self.program_id.id),
            ("date", ">=", fields.Date.context_today(self))],
            order="date", limit=5) if self.program_id else Exam.browse()
        return {
            "student": self,
            "attendance": self.overall_attendance,
            "cgpa": self.current_cgpa,
            "sgpa": self.latest_sgpa,
            "outstanding": self.outstanding_amount,
            "library_count": self.library_open_count,
            "hostel": self.hostel_room_label,
            "transport": self.transport_route_label,
            "pending_assignments": self.pending_assignment_count,
            "upcoming_exams": upcoming,
        }
