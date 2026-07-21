# -*- coding: utf-8 -*-
# Phase 3 - Expose the automation toggles and intervals in Settings. Each field
# is backed by an ir.config_parameter, so values persist and stay editable in
# Technical > System Parameters as well.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    univ_draft_reminder_enabled = fields.Boolean(
        string="Incomplete Application Reminders",
        config_parameter="inom_university_admission.draft_reminder_enabled",
        default=True,
    )
    univ_draft_reminder_days = fields.Char(
        string="Reminder Cycle (days)",
        config_parameter="inom_university_admission.draft_reminder_days",
        default="3,7,15",
        help="Comma-separated days after a draft is created to send reminders.",
    )
    univ_deadline_alert_enabled = fields.Boolean(
        string="Application Deadline Alerts",
        config_parameter="inom_university_admission.deadline_alert_enabled",
        default=True,
    )
    univ_deadline_alert_days = fields.Char(
        string="Deadline Offsets (days)",
        config_parameter="inom_university_admission.deadline_alert_days",
        default="7,3,1",
        help="Comma-separated days before a round's end date to alert "
        "applicants.",
    )
    univ_registration_notify_enabled = fields.Boolean(
        string="Registration Opening Notifications",
        config_parameter="inom_university_admission.registration_notify_enabled",
        default=True,
    )
