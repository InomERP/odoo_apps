# -*- coding: utf-8 -*-
# Phase 2 - Applicant extensions: conditional-acceptance fields and gating,
# the SMS sending helper, the portal-notification hook (a no-op here, wired by
# inom_university_portal), and document-required outbound notifications.
#
# Everything is additive. Existing methods are extended via super(); no
# existing field, workflow or method body is rewritten.
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ir.config_parameter key that gates outbound admission SMS. Off by default so
# nothing is sent until the university enables it (and an SMS gateway/IAP is
# configured in Settings). No provider credentials are ever stored here.
SMS_ENABLED_PARAM = "inom_university_admission.sms_enabled"


class UnivApplicant(models.Model):
    _inherit = "univ.applicant"

    # Mirror the offer's new "conditional" value on the stored, computed
    # offer_state so views and the portal can react to it.
    offer_state = fields.Selection(
        selection_add=[("conditional", "Conditional Offer")],
        ondelete={"conditional": "set default"},
    )

    condition_ids = fields.One2many(
        comodel_name="univ.applicant.condition",
        inverse_name="applicant_id",
        string="Admission Conditions",
    )
    # NOTE: these are intentionally NOT stored. A stored computed field on this
    # (pre-existing) model that depends on the brand-new univ.applicant.condition
    # One2many would be force-recomputed during install, before that model's
    # table exists, raising "relation univ_applicant_condition does not exist".
    # They are only read per-record (view modifiers, portal, enrolment gate),
    # so on-the-fly computation is sufficient and install-safe.
    has_conditions = fields.Boolean(
        string="Has Conditions",
        compute="_compute_condition_stats",
    )
    pending_condition_count = fields.Integer(
        string="Pending Conditions",
        compute="_compute_condition_stats",
    )
    has_pending_conditions = fields.Boolean(
        string="Conditions Pending",
        compute="_compute_condition_stats",
    )

    @api.depends("condition_ids", "condition_ids.state")
    def _compute_condition_stats(self):
        for record in self:
            conditions = record.condition_ids
            pending = conditions.filtered(lambda c: c.state == "pending")
            record.has_conditions = bool(conditions)
            record.pending_condition_count = len(pending)
            record.has_pending_conditions = bool(pending)

    # ------------------------------------------------------------------
    # Conditional offer issuing
    # ------------------------------------------------------------------
    def action_issue_conditional_offer(self):
        self.ensure_one()
        self._check_seat_available()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Issue Conditional Offer"),
            "res_model": "univ.conditional.offer.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_applicant_id": self.id},
        }

    def _on_conditions_resolved(self):
        """Called whenever a condition is cleared. When nothing is pending,
        inform the applicant and try to convert them (best-effort)."""
        for record in self:
            if record.has_pending_conditions or not record.has_conditions:
                continue
            record.message_post(
                body=record.env._("All admission conditions have been cleared.")
            )
            record._push_portal_notification(
                title=record.env._("Conditions cleared"),
                message=record.env._(
                    "All your admission conditions are now cleared. You can "
                    "proceed with the remaining admission steps.",
                ),
                url="/my/admission",
                notif_type="info",
            )
        # Records whose gates are now all met will convert; the rest are
        # skipped safely inside _try_auto_enrol.
        self._try_auto_enrol()

    # ------------------------------------------------------------------
    # Enrolment gating (extends the base checks)
    # ------------------------------------------------------------------
    def _check_can_enrol(self):
        self.ensure_one()
        if self.has_pending_conditions:
            raise UserError(
                self.env._(
                    "Cannot enrol %(name)s yet: %(count)s admission "
                    "condition(s) are still pending.",
                    name=self.name,
                    count=self.pending_condition_count,
                )
            )
        return super()._check_can_enrol()

    def _try_auto_enrol(self):
        # Never auto-convert an applicant with outstanding conditions.
        ready = self.filtered(lambda r: not r.has_pending_conditions)
        return super(UnivApplicant, ready)._try_auto_enrol()

    # ------------------------------------------------------------------
    # Decision e-mails -> also mirror to SMS + portal (additive)
    # ------------------------------------------------------------------
    def _notify_stage_email(self, template_xmlid):
        res = super()._notify_stage_email(template_xmlid)
        for record in self:
            if template_xmlid == "email_template_applicant_welcome":
                record._push_portal_notification(
                    title=record.env._("Admission confirmed"),
                    message=record.env._(
                        "Congratulations! Your admission is confirmed and your "
                        "student record has been created.",
                    ),
                    url="/my/admission",
                    notif_type="info",
                )
                record._admission_send_sms("sms_template_welcome")
            elif template_xmlid == "email_template_applicant_rejected":
                record._push_portal_notification(
                    title=record.env._("Application update"),
                    message=record.env._(
                        "There is an update on your application. Please check "
                        "your portal for details.",
                    ),
                    url="/my/admission",
                    notif_type="alert",
                )
                record._admission_send_sms("sms_template_rejected")
        return res

    # ------------------------------------------------------------------
    # Document-required outbound notification (e-mail + portal)
    # ------------------------------------------------------------------
    def _notify_documents_required(self, documents):
        """Inform the applicant that documents have been requested.

        ``documents`` is the recordset of newly assigned univ.applicant.document
        records. Sends an e-mail and pushes a portal notification.
        """
        self.ensure_one()
        template = self.env.ref(
            "inom_university_admission.email_template_documents_required",
            raise_if_not_found=False,
        )
        if template and self.email:
            template.send_mail(self.id, force_send=False)
        names = ", ".join(d.name or "" for d in documents) if documents else ""
        self._push_portal_notification(
            title=self.env._("Documents requested"),
            message=self.env._(
                "Please upload the following document(s) from your portal: "
                "%(names)s",
                names=names,
            ),
            url="/my/admission",
            notif_type="alert",
        )

    # ------------------------------------------------------------------
    # Portal notification hook (overridden by inom_university_portal)
    # ------------------------------------------------------------------
    def _push_portal_notification(
        self, title, message=False, url=False, notif_type="info"
    ):
        """No-op base hook so the admission module works standalone.

        inom_university_portal overrides this to create univ.notification
        records (it owns that model). Keeping the contract here avoids any
        circular dependency between the two modules.
        """
        return False

    def _admission_portal_user(self):
        """Resolve the portal res.users for this applicant, if one exists."""
        self.ensure_one()
        Users = self.env["res.users"].sudo()
        user = Users.browse()
        if self.partner_id:
            user = Users.search(
                [("partner_id", "=", self.partner_id.id)], limit=1
            )
        if not user and self.email:
            user = Users.search([("login", "=", self.email)], limit=1)
        return user

    # ------------------------------------------------------------------
    # SMS helper (best-effort; never breaks the admission workflow)
    # ------------------------------------------------------------------
    def _admission_sms_enabled(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(SMS_ENABLED_PARAM, "False")
            .lower()
            in ("1", "true", "yes")
        )

    def _admission_send_sms(self, template_xmlid):
        """Render an sms.template and send it to the applicant's number.

        Silent no-op when SMS is disabled, no number is present, or the SMS
        gateway raises - admission decisions must never fail because of SMS.
        """
        if not self._admission_sms_enabled():
            return
        template = self.env.ref(
            "inom_university_admission.%s" % template_xmlid,
            raise_if_not_found=False,
        )
        if not template:
            return
        for record in self:
            number = record.mobile or record.phone
            if not number:
                continue
            try:
                body = template._render_field("body", record.ids)[record.id]
                record._message_sms(body=body, sms_numbers=[number])
            except Exception as exc:  # noqa: BLE001 - SMS is best-effort
                _logger.warning(
                    "Admission SMS (%s) not sent for %s: %s",
                    template_xmlid,
                    record.display_name,
                    exc,
                )
