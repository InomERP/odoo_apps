# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class UniversityAcademicsPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_student(self):
        partner = request.env.user.partner_id
        return request.env["univ.student"].sudo().search(
            [("partner_id", "=", partner.id)], limit=1
        )

    def _get_faculty(self):
        partner = request.env.user.partner_id
        return request.env["univ.faculty"].sudo().search(
            [("partner_id", "=", partner.id)], limit=1
        )

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        student = self._get_student()
        if "subject_count" in counters:
            count = 0
            if student:
                count = request.env["univ.subject"].sudo().search_count([
                    ("program_id", "=", student.program_id.id),
                    ("semester_id", "=", student.semester_id.id),
                ])
            values["subject_count"] = count
        if "result_count" in counters:
            values["result_count"] = request.env["univ.result.semester"].sudo(
            ).search_count(
                [("student_id", "=", student.id), ("published", "=", True)]
            ) if student else 0
        if "exam_count" in counters:
            values["exam_count"] = request.env["univ.exam.schedule"].sudo(
            ).search_count([
                ("program_id", "=", student.program_id.id),
                ("semester_id", "=", student.semester_id.id),
            ]) if student else 0
        return values

    # ------------------------------------------------------------------
    # Student portal
    # ------------------------------------------------------------------
    @http.route(["/my/timetable"], type="http", auth="user", website=True)
    def portal_timetable(self, **kw):
        student = self._get_student()
        sessions = request.env["univ.timetable.session"].sudo().search(
            [("section_id", "=", student.section_id.id),
             ("state", "=", "confirmed")],
            order="date, slot_id",
        ) if student and student.section_id else request.env[
            "univ.timetable.session"].sudo()
        return request.render(
            "inom_university_academics.portal_my_timetable",
            {"page_name": "timetable", "student": student, "sessions": sessions},
        )

    @http.route(["/my/attendance"], type="http", auth="user", website=True)
    def portal_attendance(self, **kw):
        student = self._get_student()
        summaries = student.attendance_summary_ids if student else []
        return request.render(
            "inom_university_academics.portal_my_attendance",
            {"page_name": "attendance", "student": student,
             "summaries": summaries},
        )

    @http.route(["/my/exams"], type="http", auth="user", website=True)
    def portal_exams(self, **kw):
        student = self._get_student()
        schedules = request.env["univ.exam.schedule"].sudo().search([
            ("program_id", "=", student.program_id.id),
            ("semester_id", "=", student.semester_id.id),
        ], order="date") if student else request.env["univ.exam.schedule"].sudo()
        return request.render(
            "inom_university_academics.portal_my_exams",
            {"page_name": "exams", "student": student, "schedules": schedules},
        )

    @http.route(["/my/results"], type="http", auth="user", website=True)
    def portal_results(self, **kw):
        student = self._get_student()
        results = student.semester_result_ids.filtered("published") \
            if student else []
        return request.render(
            "inom_university_academics.portal_my_results",
            {"page_name": "results", "student": student, "results": results},
        )

    @http.route(["/my/transcript"], type="http", auth="user", website=True)
    def portal_transcript(self, **kw):
        student = self._get_student()
        transcript = request.env["univ.result.transcript"].sudo().search(
            [("student_id", "=", student.id)], order="version desc", limit=1
        ) if student else False
        return request.render(
            "inom_university_academics.portal_my_transcript",
            {"page_name": "transcript", "student": student,
             "transcript": transcript},
        )

    # ------------------------------------------------------------------
    # Faculty portal
    # ------------------------------------------------------------------
    @http.route(["/my/teaching"], type="http", auth="user", website=True)
    def portal_teaching(self, **kw):
        faculty = self._get_faculty()
        sessions = request.env["univ.timetable.session"].sudo().search(
            [("faculty_id", "=", faculty.id), ("state", "=", "confirmed")],
            order="date, slot_id",
        ) if faculty else request.env["univ.timetable.session"].sudo()
        return request.render(
            "inom_university_academics.portal_my_teaching",
            {"page_name": "teaching", "faculty": faculty, "sessions": sessions},
        )
