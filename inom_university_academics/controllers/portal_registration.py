# -*- coding: utf-8 -*-
# Phase 5 - Student portal for course registration. Additive controller; the
# existing academics portal controller is untouched.
from odoo import http
from odoo.http import request, content_disposition
from odoo.exceptions import UserError
from odoo.addons.portal.controllers.portal import CustomerPortal


class UniversityRegistrationPortal(CustomerPortal):

    def _reg_student(self):
        partner = request.env.user.partner_id
        return request.env["univ.student"].sudo().search(
            [("partner_id", "=", partner.id)], limit=1
        )

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "registration_count" in counters:
            student = self._reg_student()
            count = 0
            if student:
                count = request.env["univ.course.registration.line"].sudo(
                ).search_count(
                    [
                        ("student_id", "=", student.id),
                        ("state", "in", ("registered", "waitlisted")),
                    ]
                )
            values["registration_count"] = count
        return values

    def _reg_context(self):
        student = self._reg_student()
        if not student:
            return {
                "page_name": "registration",
                "student": False,
                "period": False,
                "registration": False,
                "available_offerings": [],
                "blocked_reason": False,
                "flash": None,
                "flash_type": "info",
            }
        Period = request.env["univ.registration.period"].sudo()
        Registration = request.env["univ.course.registration"].sudo()
        period = Period._get_period_for_student(student)
        registration = Registration.search(
            [("student_id", "=", student.id), ("period_id", "=", period.id)],
            limit=1,
        ) if period else Registration
        # Offerings the student has not already taken/waitlisted.
        active_offerings = registration.line_ids.filtered(
            lambda l: l.state in ("registered", "waitlisted")
        ).mapped("offering_id")
        available = period.offering_ids.filtered(
            lambda o: o.active and o not in active_offerings
        ) if period else request.env["univ.course.offering"].sudo()
        flash = request.session.pop("reg_flash", None)
        flash_type = request.session.pop("reg_flash_type", "info")
        return {
            "page_name": "registration",
            "student": student,
            "period": period,
            "registration": registration,
            "available_offerings": available,
            "blocked_reason": student._registration_blocked_reason(),
            "flash": flash,
            "flash_type": flash_type,
        }

    @http.route(["/my/registration"], type="http", auth="user", website=True)
    def portal_registration(self, **kw):
        values = self._reg_context()
        return request.render(
            "inom_university_academics.portal_my_registration", values
        )

    @http.route(
        ["/my/registration/add"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_registration_add(self, offering_id=None, **kw):
        student = self._reg_student()
        Offering = request.env["univ.course.offering"].sudo()
        offering = Offering.browse(int(offering_id)) if offering_id else Offering
        if student and offering.exists():
            period = offering.period_id
            try:
                registration = request.env[
                    "univ.course.registration"
                ].sudo()._get_or_create(student, period)
                line = registration.add_course(offering)
                if line.state == "waitlisted":
                    request.session["reg_flash"] = (
                        "Course is full - you have been added to the waitlist "
                        "(position %s)." % line.waitlist_position
                    )
                    request.session["reg_flash_type"] = "warning"
                else:
                    request.session["reg_flash"] = (
                        "Registered for %s." % offering.subject_id.name
                    )
                    request.session["reg_flash_type"] = "success"
            except UserError as exc:
                request.session["reg_flash"] = exc.args[0] if exc.args else str(exc)
                request.session["reg_flash_type"] = "danger"
        return request.redirect("/my/registration")

    @http.route(
        ["/my/registration/drop"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_registration_drop(self, line_id=None, **kw):
        student = self._reg_student()
        Line = request.env["univ.course.registration.line"].sudo()
        line = Line.browse(int(line_id)) if line_id else Line
        if student and line.exists() and line.student_id == student:
            try:
                subject = line.subject_id.name
                line.action_drop()
                request.session["reg_flash"] = "Dropped %s." % subject
                request.session["reg_flash_type"] = "success"
            except UserError as exc:
                request.session["reg_flash"] = exc.args[0] if exc.args else str(exc)
                request.session["reg_flash_type"] = "danger"
        return request.redirect("/my/registration")

    @http.route(
        ["/my/registration/confirmation"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_registration_pdf(self, **kw):
        student = self._reg_student()
        if not student:
            return request.redirect("/my")
        period = request.env["univ.registration.period"].sudo(
        )._get_period_for_student(student)
        registration = request.env["univ.course.registration"].sudo().search(
            [("student_id", "=", student.id), ("period_id", "=", period.id)],
            limit=1,
        ) if period else False
        if not registration:
            return request.redirect("/my/registration")
        pdf, _ct = request.env["ir.actions.report"].sudo()._render_qweb_pdf(
            "inom_university_academics.action_report_registration_confirmation",
            registration.ids,
        )
        return request.make_response(
            pdf,
            headers=[
                ("Content-Type", "application/pdf"),
                (
                    "Content-Disposition",
                    content_disposition("registration_confirmation.pdf"),
                ),
            ],
        )
