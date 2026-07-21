# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from urllib.parse import quote


class UniversityAdmissionWebsite(http.Controller):
    """Public-facing admission entry points (website)."""

    def _open_rounds(self):
        return (
            request.env["univ.admission.round"]
            .sudo()
            .search([("state", "=", "open")], order="start_date desc")
        )

    def _programs(self):
        return request.env["univ.program"].sudo().search([], order="name")

    def _require_application_login(self):
        """Req 1: only authenticated portal users may start an application.

        Returns a redirect response to the login/register page for public
        visitors, or ``None`` when the visitor is already signed in.
        """
        if request.env.user._is_public():
            return request.redirect(
                "/web/login?redirect=%s" % quote("/admission/apply")
            )
        return None

    @http.route(["/admission"], type="http", auth="public", website=True)
    def admission_landing(self, **kw):
        values = {
            "rounds": self._open_rounds(),
            "programs": self._programs(),
        }
        return request.render(
            "inom_university_admission.website_admission_landing", values
        )

    @http.route(
        ["/admission/apply"], type="http", auth="public", website=True
    )
    def admission_apply_form(self, **kw):
        guard = self._require_application_login()
        if guard:
            return guard
        values = {
            "rounds": self._open_rounds(),
            "programs": self._programs(),
            "countries": request.env["res.country"].sudo().search([]),
            "error": {},
            "form": {},
        }
        return request.render(
            "inom_university_admission.website_admission_form", values
        )

    @http.route(
        ["/admission/submit"],
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def admission_submit(self, **post):
        guard = self._require_application_login()
        if guard:
            return guard
        # Basic honeypot bot trap: the hidden 'website_url' field must be empty.
        if post.get("website_url"):
            return request.redirect("/admission")

        error = {}
        required = ["name", "email", "program_id", "round_id"]
        for field_name in required:
            if not post.get(field_name):
                error[field_name] = True
        if error:
            values = {
                "rounds": self._open_rounds(),
                "programs": self._programs(),
                "countries": request.env["res.country"].sudo().search([]),
                "error": error,
                "form": post,
            }
            return request.render(
                "inom_university_admission.website_admission_form", values
            )

        vals = {
            "name": post.get("name"),
            "email": post.get("email"),
            "phone": post.get("phone"),
            "mobile": post.get("mobile"),
            "program_id": int(post.get("program_id")),
            "round_id": int(post.get("round_id")),
            "city": post.get("city"),
            "source": "website",
        }
        if post.get("country_id"):
            vals["country_id"] = int(post.get("country_id"))
        if post.get("gender"):
            vals["gender"] = post.get("gender")
        if post.get("category"):
            vals["category"] = post.get("category")
        # Phase 1: capture parent/guardian + nationality and link a logged-in
        # portal user so the application shows under /my/admission. Additive.
        vals.update(request.env["univ.applicant"]._website_extra_vals(post))
        if not request.env.user._is_public():
            vals["partner_id"] = request.env.user.partner_id.id

        applicant = request.env["univ.applicant"].sudo().create(vals)
        # Acknowledgement email.
        template = request.env.ref(
            "inom_university_admission.email_template_application_ack",
            raise_if_not_found=False,
        )
        if template:
            template.sudo().send_mail(applicant.id, force_send=False)

        return request.render(
            "inom_university_admission.website_admission_thanks",
            {"applicant": applicant},
        )

    @http.route(
        ["/admission/offer/verify/<string:token>"],
        type="http",
        auth="public",
        website=True,
    )
    def admission_verify_offer(self, token, **kw):
        offer = (
            request.env["univ.applicant.offer"]
            .sudo()
            .search([("verify_token", "=", token)], limit=1)
        )
        return request.render(
            "inom_university_admission.website_offer_verify",
            {"offer": offer},
        )
