# -*- coding: utf-8 -*-
# Phase 5 - Course offering = a subject offered within a registration period
# (the "course section" with its own capacity and waitlist). Reuses subject,
# section and faculty.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivCourseOffering(models.Model):
    _name = "univ.course.offering"
    _description = "Course Offering"
    _inherit = ["mail.thread"]
    _order = "period_id, subject_id"

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    period_id = fields.Many2one(
        comodel_name="univ.registration.period",
        string="Registration Period",
        required=True,
        ondelete="cascade",
        index=True,
    )
    program_id = fields.Many2one(
        related="period_id.program_id", store=True, index=True
    )
    semester_id = fields.Many2one(
        related="period_id.semester_id", store=True, index=True
    )
    session_id = fields.Many2one(related="period_id.session_id", store=True)
    subject_id = fields.Many2one(
        comodel_name="univ.subject",
        string="Subject",
        required=True,
        ondelete="restrict",
        index=True,
    )
    subject_type = fields.Selection(
        related="subject_id.subject_type", store=True
    )
    credit_hours = fields.Float(related="subject_id.credit_hours", store=True)
    section_id = fields.Many2one(
        comodel_name="univ.section",
        string="Class Section",
        ondelete="set null",
        help="Optional class section for scheduling.",
    )
    faculty_id = fields.Many2one(
        comodel_name="univ.faculty", string="Faculty", ondelete="set null"
    )
    capacity = fields.Integer(string="Capacity", default=60)
    registration_ids = fields.One2many(
        comodel_name="univ.course.registration.line",
        inverse_name="offering_id",
        string="Registrations",
    )
    # Counts are deliberately NOT stored (computed on read) so they stay correct
    # without any install-time recompute against the new registration table.
    registered_count = fields.Integer(
        string="Registered", compute="_compute_counts"
    )
    waitlisted_count = fields.Integer(
        string="Waitlisted", compute="_compute_counts"
    )
    available_seats = fields.Integer(
        string="Available", compute="_compute_counts"
    )
    is_full = fields.Boolean(string="Full", compute="_compute_counts")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        related="period_id.company_id", store=True, index=True
    )

    _sql_constraints = [
        (
            "subject_period_uniq",
            "unique(subject_id, period_id)",
            "This subject already has an offering in this registration period.",
        ),
    ]

    @api.depends("subject_id", "period_id")
    def _compute_name(self):
        for offering in self:
            offering.name = "%s / %s" % (
                offering.subject_id.display_name or "",
                offering.period_id.name or "",
            )

    @api.depends("registration_ids.state")
    def _compute_counts(self):
        for offering in self:
            lines = offering.registration_ids
            registered = len(lines.filtered(lambda r: r.state == "registered"))
            offering.registered_count = registered
            offering.waitlisted_count = len(
                lines.filtered(lambda r: r.state == "waitlisted")
            )
            offering.available_seats = max(offering.capacity - registered, 0)
            offering.is_full = bool(
                offering.capacity and registered >= offering.capacity
            )

    @api.constrains("capacity")
    def _check_capacity(self):
        for offering in self:
            if offering.capacity < 0:
                raise ValidationError(
                    _("Capacity cannot be negative.")
                )

    def _next_waitlist_position(self):
        self.ensure_one()
        last = max(
            self.registration_ids.filtered(
                lambda r: r.state == "waitlisted"
            ).mapped("waitlist_position")
            or [0]
        )
        return last + 1

    def _promote_waitlist(self):
        """Promote the next eligible waitlisted student into a freed seat.

        Skips a waitlisted student who would exceed their credit limit and
        tries the next, so promotion never silently breaks credit rules.
        """
        self.ensure_one()
        Line = self.env["univ.course.registration.line"]
        waiters = self.registration_ids.filtered(
            lambda r: r.state == "waitlisted"
        ).sorted(key=lambda r: (r.waitlist_position, r.id))
        for waiter in waiters:
            if not (
                self.capacity
                and self.registered_count >= self.capacity
            ):
                # A seat is free; check the waiter's credit budget.
                registration = waiter.registration_id
                projected = registration.total_credits + self.credit_hours
                if projected > registration.period_id.credit_limit:
                    continue
                waiter.write(
                    {
                        "state": "registered",
                        "waitlist_position": 0,
                        "join_date": fields.Datetime.now(),
                    }
                )
                waiter._notify_promoted()
                break
