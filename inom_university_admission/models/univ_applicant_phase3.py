# -*- coding: utf-8 -*-
# Phase 3 - Scheduled applicant outreach: incomplete-application (draft)
# reminders and application-deadline alerts. Both are e-mail only, configurable
# from Settings, anti-spam, and fully logged in univ.notification.log.
#
# Additive: a single plain watermark field plus two new cron methods. No
# existing field, workflow or cron is modified.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Config parameter keys (mirrored by res.config.settings).
PARAM_DRAFT_ENABLED = "inom_university_admission.draft_reminder_enabled"
PARAM_DRAFT_DAYS = "inom_university_admission.draft_reminder_days"
PARAM_DEADLINE_ENABLED = "inom_university_admission.deadline_alert_enabled"
PARAM_DEADLINE_DAYS = "inom_university_admission.deadline_alert_days"

DEFAULT_DRAFT_DAYS = "3,7,15"
DEFAULT_DEADLINE_DAYS = "7,3,1"


def _parse_days(value):
    """Turn a '3,7,15' style string into a sorted list of positive ints."""
    result = []
    for chunk in (value or "").replace(";", ",").split(","):
        chunk = chunk.strip()
        if chunk.isdigit() and int(chunk) > 0:
            result.append(int(chunk))
    return sorted(set(result))


class UnivApplicant(models.Model):
    _inherit = "univ.applicant"

    # Highest reminder-cycle day already sent for the current draft. Plain
    # stored integer (no compute) -> install-safe. Prevents re-sending the same
    # cycle and lets reminders advance 3 -> 7 -> 15 without spamming.
    draft_reminder_day = fields.Integer(
        string="Last Draft Reminder (days)",
        default=0,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    @api.model
    def _phase3_param(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    @api.model
    def _phase3_enabled(self, key, default=True):
        raw = self._phase3_param(key, "True" if default else "False")
        return str(raw).lower() in ("1", "true", "yes")

    # ------------------------------------------------------------------
    # 1) Incomplete application (draft) reminders
    # ------------------------------------------------------------------
    @api.model
    def _cron_draft_reminders(self):
        if not self._phase3_enabled(PARAM_DRAFT_ENABLED, default=True):
            return
        thresholds = _parse_days(
            self._phase3_param(PARAM_DRAFT_DAYS, DEFAULT_DRAFT_DAYS)
        ) or _parse_days(DEFAULT_DRAFT_DAYS)
        template = self.env.ref(
            "inom_university_admission.email_template_draft_reminder",
            raise_if_not_found=False,
        )
        if not template:
            return
        Log = self.env["univ.notification.log"]
        today = fields.Date.context_today(self)
        drafts = self.search(
            [
                ("stage_id.code", "=", "draft"),
                ("stage_id.is_won", "=", False),
                ("stage_id.is_rejected", "=", False),
                ("student_id", "=", False),
            ]
        )
        for applicant in drafts:
            start = (applicant.create_date or fields.Datetime.now()).date()
            age = (today - start).days
            # Largest configured cycle whose day has elapsed.
            due = max([t for t in thresholds if t <= age], default=0)
            if not due or due <= applicant.draft_reminder_day:
                continue
            status, note = "sent", False
            if not applicant.email:
                status, note = "skipped", "No e-mail on applicant"
            else:
                try:
                    template.send_mail(applicant.id, force_send=False)
                except Exception as exc:  # noqa: BLE001 - never break the cron
                    status, note = "failed", str(exc)
                    _logger.warning(
                        "Draft reminder failed for %s: %s",
                        applicant.display_name,
                        exc,
                    )
            # Advance the watermark even when skipped so we don't retry the same
            # cycle every day for an applicant with no e-mail.
            applicant.draft_reminder_day = due
            Log.log_entry(
                "draft_reminder",
                channel="email",
                applicant_id=applicant.id,
                partner_id=applicant.partner_id.id or False,
                recipient=applicant.email or False,
                reminder_day=due,
                delivery_status=status,
                note=note,
            )

    # ------------------------------------------------------------------
    # 2) Application deadline alerts
    # ------------------------------------------------------------------
    @api.model
    def _cron_deadline_alerts(self):
        if not self._phase3_enabled(PARAM_DEADLINE_ENABLED, default=True):
            return
        offsets = _parse_days(
            self._phase3_param(PARAM_DEADLINE_DAYS, DEFAULT_DEADLINE_DAYS)
        ) or _parse_days(DEFAULT_DEADLINE_DAYS)
        template = self.env.ref(
            "inom_university_admission.email_template_deadline_alert",
            raise_if_not_found=False,
        )
        if not template:
            return
        Log = self.env["univ.notification.log"]
        today = fields.Date.context_today(self)
        rounds = self.env["univ.admission.round"].search(
            [("state", "=", "open"), ("end_date", ">=", today)]
        )
        for round_ in rounds:
            days_until = (round_.end_date - today).days
            if days_until not in offsets:
                continue
            applicants = self.search(
                [
                    ("round_id", "=", round_.id),
                    ("stage_id.is_won", "=", False),
                    ("stage_id.is_rejected", "=", False),
                ]
            )
            for applicant in applicants:
                # De-duplicate: one alert per applicant per offset per round.
                already = Log.sudo().search_count(
                    [
                        ("applicant_id", "=", applicant.id),
                        ("notif_type", "=", "deadline_alert"),
                        ("reminder_day", "=", days_until),
                        ("round_id", "=", round_.id),
                    ]
                )
                if already:
                    continue
                status, note = "sent", False
                if not applicant.email:
                    status, note = "skipped", "No e-mail on applicant"
                else:
                    try:
                        template.send_mail(applicant.id, force_send=False)
                    except Exception as exc:  # noqa: BLE001
                        status, note = "failed", str(exc)
                        _logger.warning(
                            "Deadline alert failed for %s: %s",
                            applicant.display_name,
                            exc,
                        )
                Log.log_entry(
                    "deadline_alert",
                    channel="email",
                    applicant_id=applicant.id,
                    round_id=round_.id,
                    partner_id=applicant.partner_id.id or False,
                    recipient=applicant.email or False,
                    reminder_day=days_until,
                    delivery_status=status,
                    note=note,
                )
