# -*- coding: utf-8 -*-
import base64

from odoo import _, http
from odoo.http import request, content_disposition
from odoo.addons.portal.controllers.portal import CustomerPortal

from odoo.addons.inom_university_admission.models.univ_applicant_document import (
    ALLOWED_MIMETYPES,
    MAX_FILE_SIZE,
)


class UniversityAdmissionPortal(CustomerPortal):
    """Applicant self-service portal area."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "admission_count" in counters:
            partner = request.env.user.partner_id
            values["admission_count"] = (
                request.env["univ.applicant"]
                .sudo()
                .search_count([("partner_id", "=", partner.id)])
            )
        return values

    def _get_applicants(self):
        partner = request.env.user.partner_id
        return (
            request.env["univ.applicant"]
            .sudo()
            .search([("partner_id", "=", partner.id)], order="applied_date desc")
        )

    def _get_applicant(self, applicant_id=None):
        applicants = self._get_applicants()
        if applicant_id:
            return applicants.filtered(lambda a: a.id == int(applicant_id))[:1]
        return applicants[:1]

    @http.route(["/my/admission"], type="http", auth="user", website=True)
    def portal_admission_home(self, applicant_id=None, **kw):
        applicants = self._get_applicants()
        applicant = self._get_applicant(applicant_id)
        next_action = self._compute_next_action(applicant)
        values = {
            "page_name": "admission_home",
            "applicants": applicants,
            "applicant": applicant,
            "next_action": next_action,
            "doc_checklist": self._build_doc_checklist(applicant),
            "upload_error": kw.get("doc_error"),
        }
        return request.render(
            "inom_university_admission.portal_admission_home", values
        )

    def _build_doc_checklist(self, applicant):
        """Return the documents assigned to this applicant (one per type).

        Applicants no longer choose document types; the admission team assigns
        the required documents, so the checklist is simply the applicant's own
        document records ordered by type.
        """
        if not applicant:
            return self.env["univ.applicant.document"]
        return applicant.document_ids.sorted(key=lambda d: (d.doc_type or ""))

    def _compute_next_action(self, applicant):
        if not applicant:
            return ""
        if not applicant.document_complete:
            return _("Upload and complete your document checklist.")
        if applicant.offer_state == "sent":
            return _("Review and accept your provisional offer.")
        if applicant.offer_state == "accepted" and applicant.fee_state == "pending":
            return _("Pay your admission fee to confirm your seat.")
        if applicant.is_enrolled:
            return _("Congratulations! You are enrolled.")
        return _("Your application is under review.")

    def _redirect_home(self, applicant, error=None):
        params = []
        if applicant:
            params.append("applicant_id=%s" % applicant.id)
        if error:
            params.append("doc_error=%s" % error)
        query = ("?" + "&".join(params)) if params else ""
        return request.redirect("/my/admission" + query)

    @http.route(
        ["/my/admission/documents"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_admission_upload(self, **post):
        applicant = self._get_applicant(post.get("applicant_id"))
        upload = post.get("document")
        doc_type = post.get("doc_type")
        if not applicant or not upload or not doc_type:
            return self._redirect_home(applicant, error="missing")

        data = upload.read()
        if not data:
            return self._redirect_home(applicant, error="missing")
        if len(data) > MAX_FILE_SIZE:
            return self._redirect_home(applicant, error="size")
        mimetype = getattr(upload, "mimetype", "") or ""
        if mimetype and mimetype not in ALLOWED_MIMETYPES:
            return self._redirect_home(applicant, error="type")

        # Applicants can only upload against a requirement the admission team
        # has assigned. No new document records are ever created from here.
        document = request.env["univ.applicant.document"].sudo().search(
            [
                ("applicant_id", "=", applicant.id),
                ("doc_type", "=", doc_type),
            ],
            limit=1,
        )
        if not document:
            return self._redirect_home(applicant, error="not_assigned")
        if not document.can_upload:
            return self._redirect_home(applicant, error="locked")

        document.portal_submit(base64.b64encode(data), upload.filename)
        return self._redirect_home(applicant)

    @http.route(
        ["/my/admission/document/<int:document_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_admission_document(self, document_id, **kw):
        """Securely stream a document that belongs to the logged-in applicant."""
        document = request.env["univ.applicant.document"].sudo().browse(document_id)
        if not document.exists() or not document.file:
            return request.not_found()
        partner = request.env.user.partner_id
        if document.applicant_id.partner_id.id != partner.id:
            return request.not_found()
        data = base64.b64decode(document.file)
        filename = document.file_name or "document"
        return request.make_response(
            data,
            headers=[
                ("Content-Type", "application/octet-stream"),
                ("Content-Disposition", content_disposition(filename)),
                ("Content-Length", len(data)),
            ],
        )

    @http.route(
        ["/my/admission/offer/accept"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_admission_accept_offer(self, **post):
        applicant = self._get_applicant(post.get("applicant_id"))
        if applicant and post.get("terms") and applicant.offer_state in (
            "sent",
            "conditional",
        ):
            applicant.sudo().action_accept_offer()
        return request.redirect(
            "/my/admission?applicant_id=%s" % (applicant.id if applicant else "")
        )
