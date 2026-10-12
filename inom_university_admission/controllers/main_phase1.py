# -*- coding: utf-8 -*-
# Phase 1 - Save & Resume (draft) website routes.
# These are ADDITIVE. The existing /admission/submit (single-shot) flow is not
# modified here; it continues to create-and-finalise in one step.
from odoo import http
from odoo.http import request

from .main import UniversityAdmissionWebsite
from ..models.univ_applicant_phase1 import GUARDIAN_FIELDS


class UniversityAdmissionPhase1(UniversityAdmissionWebsite):
    """Adds draft save / resume / finalise on top of the existing website
    admission controller (re-uses its _open_rounds / _programs helpers)."""

    REQUIRED_SUBMIT = ["name", "email", "program_id", "round_id"]

    def _draft_stage(self):
        return request.env.ref(
            "inom_university_admission.stage_draft", raise_if_not_found=False)

    def _form_context(self, form=None, error=None):
        return {
            "rounds": self._open_rounds(),
            "programs": self._programs(),
            "countries": request.env["res.country"].sudo().search([]),
            "error": error or {},
            "form": form or {},
        }

    def _collect_vals(self, post):
        """Build applicant vals from a POST dict (core + guardian/nationality).
        Links the partner when the visitor is a logged-in portal user."""
        vals = {}
        for f in ("name", "email", "phone", "mobile", "city"):
            if f in post:
                vals[f] = post.get(f)
        if post.get("program_id"):
            vals["program_id"] = int(post["program_id"])
        if post.get("round_id"):
            vals["round_id"] = int(post["round_id"])
        if post.get("country_id"):
            vals["country_id"] = int(post["country_id"])
        if post.get("gender"):
            vals["gender"] = post.get("gender")
        if post.get("category"):
            vals["category"] = post.get("category")
        vals.update(request.env["univ.applicant"]._website_extra_vals(post))
        user = request.env.user
        if not user._is_public():
            vals["partner_id"] = user.partner_id.id
        return vals

    def _find_draft(self, token):
        if not token:
            return request.env["univ.applicant"].sudo().browse()
        return request.env["univ.applicant"].sudo().search(
            [("access_token", "=", token)], limit=1)

    # ------------------------------------------------------------------
    # Save draft (create or update a partially filled application)
    # ------------------------------------------------------------------
    @http.route(["/admission/apply/draft"], type="http", auth="public",
                website=True, methods=["POST"])
    def admission_save_draft(self, **post):
        if post.get("website_url"):
            return request.redirect("/admission")
        # A draft only needs a name so the record is identifiable.
        if not post.get("name"):
            return request.render(
                "inom_university_admission.website_admission_form",
                self._form_context(form=post, error={"name": True}))

        vals = self._collect_vals(post)
        applicant = self._find_draft(post.get("resume_token"))
        if applicant:
            applicant.write(vals)
        else:
            vals["source"] = "website"
            draft_stage = self._draft_stage()
            if draft_stage:
                vals["stage_id"] = draft_stage.id
            applicant = request.env["univ.applicant"].sudo().create(vals)

        resume_url = "/admission/resume/%s" % applicant.access_token
        return request.render(
            "inom_university_admission.website_admission_draft_saved",
            {"applicant": applicant, "resume_url": resume_url})

    # ------------------------------------------------------------------
    # Resume a draft (render the form pre-filled)
    # ------------------------------------------------------------------
    @http.route(["/admission/resume/<string:token>"], type="http",
                auth="public", website=True)
    def admission_resume(self, token, **kw):
        applicant = self._find_draft(token)
        if not applicant:
            return request.redirect("/admission/apply")
        form = {
            "name": applicant.name or "",
            "email": applicant.email or "",
            "phone": applicant.phone or "",
            "mobile": applicant.mobile or "",
            "city": applicant.city or "",
            "program_id": str(applicant.program_id.id) if applicant.program_id else "",
            "round_id": str(applicant.round_id.id) if applicant.round_id else "",
            "resume_token": token,
        }
        for f in GUARDIAN_FIELDS:
            form[f] = getattr(applicant, f) or ""
        return request.render(
            "inom_university_admission.website_admission_form",
            self._form_context(form=form))

    # ------------------------------------------------------------------
    # Finalise a resumed draft (update + move into the normal pipeline)
    # ------------------------------------------------------------------
    @http.route(["/admission/apply/finalize"], type="http", auth="public",
                website=True, methods=["POST"])
    def admission_finalize(self, **post):
        if post.get("website_url"):
            return request.redirect("/admission")
        applicant = self._find_draft(post.get("resume_token"))
        if not applicant:
            # No matching draft -> send the visitor back to a fresh form.
            return request.redirect("/admission/apply")

        error = {f: True for f in self.REQUIRED_SUBMIT if not post.get(f)}
        if error:
            form = dict(post)
            form["resume_token"] = post.get("resume_token") or ""
            return request.render(
                "inom_university_admission.website_admission_form",
                self._form_context(form=form, error=error))

        vals = self._collect_vals(post)
        # Leave the Draft stage and enter the standard pipeline.
        # _default_stage_id() returns an id (int), not a recordset.
        default_stage_id = request.env["univ.applicant"].sudo()._default_stage_id()
        if default_stage_id:
            vals["stage_id"] = default_stage_id
        applicant.write(vals)

        template = request.env.ref(
            "inom_university_admission.email_template_application_ack",
            raise_if_not_found=False)
        if template:
            template.sudo().send_mail(applicant.id, force_send=False)

        return request.render(
            "inom_university_admission.website_admission_thanks",
            {"applicant": applicant})
