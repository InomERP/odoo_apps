# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class CampusPortal(CustomerPortal):

    @http.route(["/my/dashboard"], type="http", auth="user", website=True)
    def portal_dashboard(self, **kw):
        partner = request.env.user.partner_id
        student = request.env["univ.student"].sudo().search(
            [("partner_id", "=", partner.id)], limit=1)
        values = {"page_name": "dashboard", "student": student}
        if student:
            values.update(student.get_campus_dashboard())
        return request.render(
            "inom_university_campus_services.portal_dashboard", values)

    @http.route(["/my/teaching"], type="http", auth="user", website=True)
    def portal_teaching(self, **kw):
        partner = request.env.user.partner_id
        faculty = request.env["univ.faculty"].sudo().search(
            [("partner_id", "=", partner.id)], limit=1)
        data = {"page_name": "teaching", "faculty": faculty}
        if faculty:
            subjects = faculty.subject_ids
            assignments = request.env["univ.assignment"].sudo().search(
                [("subject_id", "in", subjects.ids)], order="due_date desc")
            materials = request.env["univ.lms.material"].sudo().search(
                [("subject_id", "in", subjects.ids)])
            data.update({
                "subjects": subjects,
                "assignments": assignments,
                "materials": materials,
                "to_grade": assignments.mapped("submission_ids").filtered(
                    lambda s: s.state == "submitted"),
            })
        return request.render(
            "inom_university_campus_services.portal_teaching", data)
