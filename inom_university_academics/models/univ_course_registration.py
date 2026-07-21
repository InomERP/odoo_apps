# -*- coding: utf-8 -*-
# Phase 5 - Course registration (header) + registration line (the add/drop
# unit). Enforces the registration window, the per-period credit limit,
# subject prerequisites, the Phase 4 deposit gate, and the course-section
# waitlist with auto-promotion.
from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivCourseRegistration(models.Model):
    _name = "univ.course.registration"
    _description = "Course Registration"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    student_id = fields.Many2one(
        comodel_name="univ.student",
        string="Student",
        required=True,
        ondelete="cascade",
        index=True,
    )
    period_id = fields.Many2one(
        comodel_name="univ.registration.period",
        string="Registration Period",
        required=True,
        ondelete="restrict",
        index=True,
    )
    program_id = fields.Many2one(
        related="period_id.program_id", store=True, index=True
    )
    semester_id = fields.Many2one(
        related="period_id.semester_id", store=True, index=True
    )
    session_id = fields.Many2one(related="period_id.session_id", store=True)
    registration_date = fields.Datetime(
        string="Registration Date", default=fields.Datetime.now, copy=False
    )
    credit_limit = fields.Float(
        related="period_id.credit_limit", string="Credit Limit"
    )
    line_ids = fields.One2many(
        comodel_name="univ.course.registration.line",
        inverse_name="registration_id",
        string="Courses",
    )
    total_credits = fields.Float(
        string="Registered Credits",
        compute="_compute_total_credits",
        store=True,
    )
    registered_course_count = fields.Integer(
        string="Registered Courses",
        compute="_compute_total_credits",
        store=True,
    )
    partner_id = fields.Many2one(
        related="student_id.partner_id", store=True
    )
    company_id = fields.Many2one(
        related="student_id.company_id", store=True, index=True
    )

    _sql_constraints = [
        (
            "student_period_uniq",
            "unique(student_id, period_id)",
            "A student already has a registration for this period.",
        ),
    ]

    @api.depends("student_id", "period_id")
    def _compute_name(self):
        for record in self:
            record.name = "%s - %s" % (
                record.student_id.display_name or "",
                record.period_id.name or "",
            )

    @api.depends("line_ids.state", "line_ids.credit_hours")
    def _compute_total_credits(self):
        for record in self:
            registered = record.line_ids.filtered(
                lambda l: l.state == "registered"
            )
            record.total_credits = sum(registered.mapped("credit_hours"))
            record.registered_course_count = len(registered)

    # ------------------------------------------------------------------
    # Entry point + add
    # ------------------------------------------------------------------
    @api.model
    def _get_or_create(self, student, period):
        registration = self.search(
            [("student_id", "=", student.id), ("period_id", "=", period.id)],
            limit=1,
        )
        if not registration:
            registration = self.create(
                {"student_id": student.id, "period_id": period.id}
            )
        return registration

    def add_course(self, offering):
        """Add (register or waitlist) a course for this student. All Phase 5
        gates are enforced here. Returns the created registration line."""
        self.ensure_one()
        student = self.student_id
        period = self.period_id

        # G) Deposit / enrolment gate (reuses Phase 4 - no payment logic here).
        reason = student._registration_blocked_reason()
        if reason:
            raise UserError(reason)

        # D) Registration window.
        period._ensure_open()

        # Duplicate guard - one active line per offering.
        active = self.line_ids.filtered(
            lambda l: l.offering_id == offering
            and l.state in ("registered", "waitlisted")
        )
        if active:
            raise UserError(
                self.env._(
                    "You are already %(state)s for %(subject)s.",
                    state=dict(
                        active._fields["state"].selection
                    ).get(active[0].state),
                    subject=offering.subject_id.display_name,
                )
            )

        # C) Prerequisites.
        missing = offering.subject_id.prerequisite_ids - student._passed_subject_ids()
        if missing:
            raise UserError(
                self.env._(
                    "Cannot register %(subject)s: prerequisite(s) not "
                    "completed - %(missing)s.",
                    subject=offering.subject_id.display_name,
                    missing=", ".join(missing.mapped("display_name")),
                )
            )

        # F) Capacity -> waitlist when full.
        if offering.is_full:
            line = self.env["univ.course.registration.line"].create(
                {
                    "registration_id": self.id,
                    "offering_id": offering.id,
                    "state": "waitlisted",
                    "waitlist_position": offering._next_waitlist_position(),
                }
            )
            self.message_post(
                body=self.env._(
                    "Waitlisted for %(subject)s (position %(pos)s).",
                    subject=offering.subject_id.display_name,
                    pos=line.waitlist_position,
                )
            )
            return line

        # B) Credit limit (registered courses only).
        projected = self.total_credits + offering.credit_hours
        if projected > period.credit_limit:
            raise UserError(
                self.env._(
                    "Credit limit exceeded: registering %(subject)s would "
                    "bring you to %(total)s credits, above the limit of "
                    "%(limit)s.",
                    subject=offering.subject_id.display_name,
                    total=projected,
                    limit=period.credit_limit,
                )
            )
        line = self.env["univ.course.registration.line"].create(
            {
                "registration_id": self.id,
                "offering_id": offering.id,
                "state": "registered",
            }
        )
        self.message_post(
            body=self.env._(
                "Registered %(subject)s (%(credits)s credits).",
                subject=offering.subject_id.display_name,
                credits=offering.credit_hours,
            )
        )
        return line

    def action_print_confirmation(self):
        self.ensure_one()
        return self.env.ref(
            "inom_university_academics.action_report_registration_confirmation"
        ).report_action(self)


class UnivCourseRegistrationLine(models.Model):
    _name = "univ.course.registration.line"
    _description = "Course Registration Line"
    _inherit = ["mail.thread"]
    _order = "registration_id, waitlist_position, id"

    registration_id = fields.Many2one(
        comodel_name="univ.course.registration",
        string="Registration",
        required=True,
        ondelete="cascade",
        index=True,
    )
    student_id = fields.Many2one(
        related="registration_id.student_id", store=True, index=True
    )
    period_id = fields.Many2one(
        related="registration_id.period_id", store=True, index=True
    )
    offering_id = fields.Many2one(
        comodel_name="univ.course.offering",
        string="Course Offering",
        required=True,
        ondelete="restrict",
        index=True,
    )
    subject_id = fields.Many2one(
        related="offering_id.subject_id", store=True, index=True
    )
    subject_type = fields.Selection(
        related="offering_id.subject_type", store=True
    )
    credit_hours = fields.Float(related="offering_id.credit_hours", store=True)
    state = fields.Selection(
        selection=[
            ("registered", "Registered"),
            ("waitlisted", "Waitlisted"),
            ("dropped", "Dropped"),
        ],
        string="Status",
        default="registered",
        required=True,
        tracking=True,
        index=True,
    )
    waitlist_position = fields.Integer(string="Waitlist Position")
    join_date = fields.Datetime(
        string="Joined On", default=fields.Datetime.now, copy=False
    )
    drop_date = fields.Datetime(string="Dropped On", copy=False)
    company_id = fields.Many2one(
        related="registration_id.company_id", store=True, index=True
    )

    def action_drop(self):
        """Drop a course within the window; auto-promote the next waitlister."""
        for line in self:
            period = line.registration_id.period_id
            period._ensure_open()
            if line.state == "dropped":
                continue
            was_registered = line.state == "registered"
            offering = line.offering_id
            line.write(
                {"state": "dropped", "drop_date": fields.Datetime.now()}
            )
            line.registration_id.message_post(
                body=self.env._(
                    "Dropped %(subject)s.",
                    subject=offering.subject_id.display_name,
                )
            )
            if was_registered:
                offering._promote_waitlist()
        return True

    # ------------------------------------------------------------------
    # Waitlist promotion notification (existing mechanisms)
    # ------------------------------------------------------------------
    def _notify_promoted(self):
        """Notify a student promoted off the waitlist. Uses chatter + the
        existing mail template; the portal notification centre is wired by
        inom_university_portal via the _emit_portal_notification hook."""
        for line in self:
            line.registration_id.message_post(
                body=line.env._(
                    "Promoted from the waitlist into %(subject)s.",
                    subject=line.subject_id.display_name,
                )
            )
            template = self.env.ref(
                "inom_university_academics.email_template_waitlist_promoted",
                raise_if_not_found=False,
            )
            if template and line.student_id.email:
                template.send_mail(line.id, force_send=False)
            line._emit_portal_notification(
                title=line.env._("Waitlist promotion"),
                message=line.env._(
                    "A seat opened up and you are now registered for %(subject)s.",
                    subject=line.subject_id.display_name,
                ),
                url="/my/registration",
            )

    def _emit_portal_notification(self, title, message=False, url=False):
        """No-op base hook (overridden by inom_university_portal)."""
        return False
