# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class LibraryPortal(CustomerPortal):

    def _library_member(self):
        partner = request.env.user.partner_id
        student = request.env["univ.student"].sudo().search(
            [("partner_id", "=", partner.id)], limit=1)
        domain = [("student_id", "=", student.id)] if student else \
            [("faculty_id.partner_id", "=", partner.id)]
        return request.env["univ.library.member"].sudo().search(domain, limit=1)

    @http.route(["/my/library"], type="http", auth="user", website=True)
    def portal_library(self, **kw):
        member = self._library_member()
        issues = request.env["univ.library.issue"].sudo().search(
            [("member_id", "=", member.id)], order="issue_date desc") \
            if member else request.env["univ.library.issue"].sudo()
        return request.render("inom_university_library.portal_my_library", {
            "page_name": "library", "member": member,
            "issues": issues,
            "current": issues.filtered(lambda i: i.state in ("issued", "overdue")),
            "fines": issues.mapped("fine_ids").filtered(
                lambda f: f.state != "cancelled"),
        })
