# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class UniversityPortal(CustomerPortal):
    """Phase 1 portal: read-only profile and a welcome dashboard placeholder.

    Editing and transactional features (fees, results, attendance) arrive in
    later phases; this phase only surfaces the student's own profile.
    """

    def _get_university_student(self):
        partner = request.env.user.partner_id
        return (
            request.env["univ.student"]
            .sudo()
            .search([("partner_id", "=", partner.id)], limit=1)
        )

    @http.route(["/my/university"], type="http", auth="user", website=True)
    def portal_university_home(self, **kw):
        student = self._get_university_student()
        values = {
            "page_name": "university_home",
            "student": student,
            "coming_soon_tiles": [
                {"name": "My Fees", "icon": "fa-money"},
                {"name": "My Results", "icon": "fa-graduation-cap"},
                {"name": "My Attendance", "icon": "fa-calendar-check-o"},
                {"name": "My Timetable", "icon": "fa-clock-o"},
            ],
        }
        return request.render(
            "inom_university_core.portal_university_home", values
        )

    @http.route(["/my/university/profile"], type="http", auth="user", website=True)
    def portal_university_profile(self, **kw):
        student = self._get_university_student()
        if not student:
            return request.redirect("/my")
        values = {
            "page_name": "university_profile",
            "student": student,
        }
        return request.render(
            "inom_university_core.portal_university_profile", values
        )
