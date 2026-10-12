# -*- coding: utf-8 -*-
# Phase 3 - Automated notification audit log. Every scheduled notification
# (draft reminder, deadline alert, registration-opening) writes one row here so
# admins can audit who was contacted, how, when and with what result.
from odoo import api, fields, models

NOTIF_TYPE_SELECTION = [
    ("draft_reminder", "Incomplete Application Reminder"),
    ("deadline_alert", "Application Deadline Alert"),
    ("registration_open", "Registration Opening"),
]


class UnivNotificationLog(models.Model):
    _name = "univ.notification.log"
    _description = "Admission Notification Log"
    _order = "sent_on desc, id desc"

    name = fields.Char(string="Summary", compute="_compute_name", store=True)
    notif_type = fields.Selection(
        selection=NOTIF_TYPE_SELECTION,
        string="Notification Type",
        required=True,
        index=True,
    )
    channel = fields.Selection(
        selection=[("email", "E-mail"), ("portal", "Portal")],
        string="Channel",
        default="email",
        required=True,
    )
    applicant_id = fields.Many2one(
        comodel_name="univ.applicant",
        string="Applicant",
        ondelete="cascade",
        index=True,
    )
    student_id = fields.Many2one(
        comodel_name="univ.student",
        string="Student",
        ondelete="cascade",
        index=True,
    )
    round_id = fields.Many2one(
        comodel_name="univ.admission.round",
        string="Round",
        ondelete="set null",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Recipient"
    )
    recipient = fields.Char(
        string="Recipient Address",
        help="E-mail address or portal login the notification was sent to.",
    )
    reminder_day = fields.Integer(
        string="Cycle / Offset (days)",
        help="Reminder cycle day or deadline offset this entry corresponds to.",
    )
    sent_on = fields.Datetime(
        string="Sent On", default=fields.Datetime.now, index=True
    )
    delivery_status = fields.Selection(
        selection=[
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("skipped", "Skipped"),
        ],
        string="Delivery Status",
        default="sent",
        required=True,
    )
    note = fields.Text(string="Note")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        default=lambda self: self.env.company,
        index=True,
    )

    @api.depends("notif_type", "applicant_id", "student_id", "reminder_day")
    def _compute_name(self):
        type_labels = dict(NOTIF_TYPE_SELECTION)
        for record in self:
            who = (
                record.applicant_id.display_name
                or record.student_id.display_name
                or ""
            )
            label = type_labels.get(record.notif_type, record.notif_type or "")
            suffix = " (D%s)" % record.reminder_day if record.reminder_day else ""
            record.name = "%s - %s%s" % (label, who, suffix)

    @api.model
    def log_entry(self, notif_type, **vals):
        """Create one audit-log row. Always sudo-safe; never raises into a
        cron. ``vals`` accepts channel, applicant_id, student_id, round_id,
        partner_id, recipient, reminder_day, delivery_status, note."""
        vals["notif_type"] = notif_type
        return self.sudo().create(vals)
