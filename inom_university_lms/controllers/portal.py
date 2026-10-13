# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class LmsPortal(CustomerPortal):

    def _student(self):
        return request.env["univ.student"].sudo().search(
            [("partner_id", "=", request.env.user.partner_id.id)], limit=1)

    @http.route(["/my/lms"], type="http", auth="user", website=True)
    def portal_lms(self, **kw):
        student = self._student()
        subject_ids = student.program_id.subject_ids.ids if student and \
            hasattr(student.program_id, "subject_ids") else []
        domain = [("state", "=", "published")]
        if subject_ids:
            domain.append(("subject_id", "in", subject_ids))
        materials = request.env["univ.lms.material"].sudo().search(
            domain, order="subject_id, sequence")
        return request.render("inom_university_lms.portal_my_lms", {
            "page_name": "lms", "student": student, "materials": materials})

    @http.route(["/my/assignments"], type="http", auth="user", website=True)
    def portal_assignments(self, **kw):
        student = self._student()
        assignments = request.env["univ.assignment"].sudo().search(
            [("state", "=", "published")], order="due_date desc")
        submissions = request.env["univ.assignment.submission"].sudo().search(
            [("student_id", "=", student.id)]) if student else \
            request.env["univ.assignment.submission"].sudo()
        sub_map = {s.assignment_id.id: s for s in submissions}
        return request.render("inom_university_lms.portal_my_assignments", {
            "page_name": "assignments", "student": student,
            "assignments": assignments, "sub_map": sub_map})

    @http.route(["/my/assignments/submit"], type="http", auth="user",
                website=True, methods=["POST"])
    def portal_assignment_submit(self, **post):
        student = self._student()
        assignment_id = int(post.get("assignment_id", 0))
        if student and assignment_id:
            existing = request.env["univ.assignment.submission"].sudo().search([
                ("assignment_id", "=", assignment_id),
                ("student_id", "=", student.id)], limit=1)
            if not existing:
                sub = request.env["univ.assignment.submission"].sudo().create({
                    "assignment_id": assignment_id,
                    "student_id": student.id,
                    "note": post.get("note"),
                })
                upload = post.get("file")
                if upload:
                    attachment = request.env["ir.attachment"].sudo().create({
                        "name": upload.filename,
                        "datas": __import__("base64").b64encode(upload.read()),
                        "res_model": "univ.assignment.submission",
                        "res_id": sub.id,
                    })
                    sub.attachment_ids = [(4, attachment.id)]
        return request.redirect("/my/assignments")
