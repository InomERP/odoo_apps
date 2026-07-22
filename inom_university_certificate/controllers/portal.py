# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, content_disposition
from odoo.addons.portal.controllers.portal import CustomerPortal


class CertificatePortal(CustomerPortal):

    def _student(self):
        return request.env["univ.student"].sudo().search(
            [("partner_id", "=", request.env.user.partner_id.id)], limit=1)

    @http.route(["/my/certificates/<int:cert_id>/download"], type="http",
                auth="user", website=True)
    def portal_certificate_download(self, cert_id, **kw):
        student = self._student()
        cert = request.env["univ.certificate"].sudo().browse(cert_id)
        # Only the owning student may download, and only once issued.
        if (not cert.exists() or not student
                or cert.student_id.id != student.id
                or cert.state not in ("issued", "superseded")):
            return request.redirect("/my/certificates")
        pdf, _content_type = request.env["ir.actions.report"].sudo()._render_qweb_pdf(
            "inom_university_certificate.report_certificate", [cert.id])
        filename = "Certificate-%s.pdf" % (cert.name or cert.id)
        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf)),
            ("Content-Disposition", content_disposition(filename)),
        ]
        return request.make_response(pdf, headers=headers)

    @http.route(["/my/certificates"], type="http", auth="user", website=True)
    def portal_certificates(self, **kw):
        student = self._student()
        certs = request.env["univ.certificate"].sudo().search(
            [("student_id", "=", student.id)], order="create_date desc") \
            if student else request.env["univ.certificate"].sudo()
        templates = request.env["univ.certificate.template"].sudo().search(
            [("cert_type", "!=", "id_card")])
        return request.render("inom_university_certificate.portal_my_certificates", {
            "page_name": "certificates", "student": student,
            "certs": certs, "templates": templates})

    @http.route(["/my/certificates/request"], type="http", auth="user",
                website=True, methods=["POST"])
    def portal_certificate_request(self, **post):
        student = self._student()
        template_id = int(post.get("template_id", 0))
        if student and template_id:
            request.env["univ.certificate"].sudo().create({
                "student_id": student.id,
                "template_id": template_id,
                "purpose": post.get("purpose"),
            })
        return request.redirect("/my/certificates")
