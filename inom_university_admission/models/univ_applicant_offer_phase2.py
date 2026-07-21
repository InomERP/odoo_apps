# -*- coding: utf-8 -*-
# Phase 2 - Offer model extensions for conditional acceptance + multi-channel
# decision notifications (SMS + portal). Additive inherit; the original
# action_send()/action_accept() behaviour is preserved and only extended.
from odoo import _, api, fields, models


class UnivApplicantOffer(models.Model):
    _inherit = "univ.applicant.offer"

    # Extend the existing status with a "Conditional Offer" value. selection_add
    # keeps every original value intact and is the supported, upgrade-safe way
    # to widen a Selection.
    state = fields.Selection(
        selection_add=[("conditional", "Conditional Offer")],
        ondelete={"conditional": "set default"},
    )
    # Not stored: a stored compute depending on the new condition One2many
    # would recompute during install before univ_applicant_condition exists.
    is_conditional = fields.Boolean(
        string="Conditional",
        compute="_compute_is_conditional",
    )
    condition_ids = fields.One2many(
        comodel_name="univ.applicant.condition",
        inverse_name="offer_id",
        string="Conditions",
    )

    @api.depends("condition_ids")
    def _compute_is_conditional(self):
        for record in self:
            record.is_conditional = bool(record.condition_ids)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------
    def action_send(self):
        """Original unconditional send + Phase 2 SMS / portal notification."""
        res = super().action_send()
        for record in self:
            record.applicant_id._push_portal_notification(
                title=_("Admission offer sent"),
                message=_(
                    "A provisional admission offer (%(ref)s) has been sent to "
                    "you. Please review and accept it from your portal.",
                    ref=record.name or "",
                ),
                url="/my/admission",
                notif_type="info",
            )
            record.applicant_id._admission_send_sms("sms_template_offer_sent")
        return res

    def action_send_conditional(self):
        """Issue the offer subject to its outstanding conditions."""
        for record in self:
            record.write(
                {"state": "conditional", "issued_on": fields.Datetime.now()}
            )
            template = self.env.ref(
                "inom_university_admission.email_template_offer_conditional",
                raise_if_not_found=False,
            )
            if template and record.applicant_id.email:
                template.send_mail(record.id, force_send=False)
            record.applicant_id._push_portal_notification(
                title=_("Conditional offer issued"),
                message=_(
                    "You have received a conditional admission offer. Please "
                    "review the pending conditions in your portal.",
                ),
                url="/my/admission",
                notif_type="info",
            )
            record.applicant_id._admission_send_sms(
                "sms_template_offer_conditional"
            )

    # ------------------------------------------------------------------
    # Acceptance (also allow accepting a conditional offer)
    # ------------------------------------------------------------------
    def action_accept(self):
        # A conditional offer can be accepted; its conditions still gate
        # enrolment via univ.applicant._check_can_enrol.
        conditional = self.filtered(lambda o: o.state == "conditional")
        conditional.write(
            {
                "state": "accepted",
                "accepted_on": fields.Datetime.now(),
                "terms_accepted": True,
            }
        )
        remaining = self - conditional
        if remaining:
            super(UnivApplicantOffer, remaining).action_accept()
        return True
