# -*- coding: utf-8 -*-
# Phase 3 - Course registration-opening notifications. When a round's
# registration window opens, the cohort admitted through that round is notified
# by e-mail and portal notification (the portal side is wired by
# inom_university_portal via the _emit_registration_portal_notifications hook).
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PARAM_REGISTRATION_ENABLED = (
    "inom_university_admission.registration_notify_enabled"
)


class UnivAdmissionRound(models.Model):
    _inherit = "univ.admission.round"

    registration_open_date = fields.Datetime(
        string="Registration Opens On",
        tracking=True,
        help="When course registration opens for students admitted in this "
        "round. Leave empty to disable the registration-opening broadcast.",
    )
    registration_notified = fields.Boolean(
        string="Registration Opening Notified",
        default=False,
        copy=False,
        help="Set once the registration-opening broadcast has been sent.",
    )

    # ------------------------------------------------------------------
    # Eligible cohort
    # ------------------------------------------------------------------
    def _registration_students(self):
        """Students admitted through this round (the cohort for whom
        registration is opening)."""
        self.ensure_one()
        applicants = self.env["univ.applicant"].search(
            [("round_id", "=", self.id), ("student_id", "!=", False)]
        )
        return applicants.mapped("student_id")

    # ------------------------------------------------------------------
    # Portal hook (overridden by inom_university_portal)
    # ------------------------------------------------------------------
    def _emit_registration_portal_notifications(
        self, students, title, message, url
    ):
        """No-op base hook so admission works standalone. The portal module
        overrides this to create univ.notification records and log the portal
        channel deliveries."""
        return False

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_registration_open_notify(self):
        enabled = str(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(PARAM_REGISTRATION_ENABLED, "True")
        ).lower() in ("1", "true", "yes")
        if not enabled:
            return
        template = self.env.ref(
            "inom_university_admission.email_template_registration_open",
            raise_if_not_found=False,
        )
        Log = self.env["univ.notification.log"]
        now = fields.Datetime.now()
        rounds = self.search(
            [
                ("registration_open_date", "!=", False),
                ("registration_open_date", "<=", now),
                ("registration_notified", "=", False),
            ]
        )
        for round_ in rounds:
            students = round_._registration_students()
            title = self.env._("Course registration is open")
            message = self.env._(
                "Course registration for %(round)s is now open. Please log in "
                "to your portal to proceed.",
                round=round_.name,
            )
            # E-mail each student.
            for student in students:
                status, note = "sent", False
                if not template:
                    status, note = "skipped", "Template missing"
                elif not student.email:
                    status, note = "skipped", "No e-mail on student"
                else:
                    try:
                        template.send_mail(student.id, force_send=False)
                    except Exception as exc:  # noqa: BLE001
                        status, note = "failed", str(exc)
                        _logger.warning(
                            "Registration e-mail failed for %s: %s",
                            student.display_name,
                            exc,
                        )
                Log.log_entry(
                    "registration_open",
                    channel="email",
                    student_id=student.id,
                    round_id=round_.id,
                    partner_id=student.partner_id.id or False,
                    recipient=student.email or False,
                    delivery_status=status,
                    note=note,
                )
            # Portal notifications (wired in inom_university_portal).
            round_._emit_registration_portal_notifications(
                students, title, message, "/my/home"
            )
            round_.registration_notified = True
