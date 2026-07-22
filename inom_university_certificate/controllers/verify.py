# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class CertificateVerify(http.Controller):

    @http.route(["/certificate/verify/<string:number>"], type="http",
                auth="public", website=True, sitemap=False)
    def verify(self, number, **kw):
        cert = request.env["univ.certificate"].sudo().search(
            [("name", "=", number)], limit=1)
        card = request.env["univ.id.card"].sudo().search(
            [("name", "=", number)], limit=1) if not cert else False
        return request.render("inom_university_certificate.verify_page", {
            "number": number, "cert": cert, "card": card})
