# -*- coding: utf-8 -*-
# Phase 5 - Student helpers for course registration: passed-subject lookup
# (prerequisites) and the registration eligibility gate that reuses the Phase 4
# deposit check on the linked admission applicant.
from odoo import fields, models


class UnivStudent(models.Model):
    _inherit = "univ.student"

    course_registration_ids = fields.One2many(
        comodel_name="univ.course.registration",
        inverse_name="student_id",
        string="Course Registrations",
    )
    registration_line_ids = fields.One2many(
        comodel_name="univ.course.registration.line",
        inverse_name="student_id",
        string="Registered Courses",
    )

    def _passed_subject_ids(self):
        """Subjects this student has passed (approved exam results)."""
        self.ensure_one()
        lines = self.env["univ.exam.result.line"].sudo().search(
            [
                ("student_id", "=", self.id),
                ("is_pass", "=", True),
                ("state", "=", "approved"),
            ]
        )
        return lines.mapped("subject_id")

    def _registration_blocked_reason(self):
        """Return a user-facing message if course registration is NOT allowed,
        else False. Enrolment + Phase 4 deposit gate, no payment logic here."""
        self.ensure_one()
        if self.state not in ("enrolled", "active"):
            return self.env._(
                "Course registration is only available to enrolled students."
            )
        # Reuse the Phase 4 deposit state on the linked admission applicant.
        applicant = self.env["univ.applicant"].sudo().search(
            [("student_id", "=", self.id)], limit=1
        )
        if (
            applicant
            and applicant.deposit_required
            and applicant.deposit_state != "paid"
        ):
            return self.env._(
                "Course registration is blocked until the admission deposit "
                "is fully paid."
            )
        return False
