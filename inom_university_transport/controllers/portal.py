# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class TransportPortal(CustomerPortal):

    @http.route(["/my/transport"], type="http", auth="user", website=True)
    def portal_transport(self, **kw):
        student = request.env["univ.student"].sudo().search(
            [("partner_id", "=", request.env.user.partner_id.id)], limit=1)
        subs = request.env["univ.transport.subscription"].sudo().search(
            [("student_id", "=", student.id),
             ("state", "in", ("fee_added", "issued"))],
            order="create_date desc") if student else []
        return request.render("inom_university_transport.portal_my_transport", {
            "page_name": "transport", "student": student, "subscriptions": subs})
