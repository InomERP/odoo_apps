# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class HostelPortal(CustomerPortal):

    def _student(self):
        return request.env["univ.student"].sudo().search(
            [("partner_id", "=", request.env.user.partner_id.id)], limit=1)

    @http.route(["/my/hostel"], type="http", auth="user", website=True)
    def portal_hostel(self, **kw):
        student = self._student()
        allotment = request.env["univ.hostel.allotment"].sudo().search(
            [("student_id", "=", student.id),
             ("state", "in", ("allotted", "checked_in"))], limit=1) \
            if student else False
        complaints = request.env["univ.hostel.complaint"].sudo().search(
            [("student_id", "=", student.id)], order="create_date desc") \
            if student else []
        return request.render("inom_university_hostel.portal_my_hostel", {
            "page_name": "hostel", "student": student,
            "allotment": allotment, "complaints": complaints})

    @http.route(["/my/hostel/complaint"], type="http", auth="user",
                website=True, methods=["POST"])
    def portal_hostel_complaint(self, **post):
        student = self._student()
        if student and post.get("subject"):
            request.env["univ.hostel.complaint"].sudo().create({
                "name": post.get("subject"),
                "student_id": student.id,
                "description": post.get("description"),
                "category": post.get("category", "maintenance"),
            })
        return request.redirect("/my/hostel")
