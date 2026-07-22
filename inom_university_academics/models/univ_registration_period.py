# -*- coding: utf-8 -*-
# Phase 5 - Course registration period (the configurable add/drop window) and
# the per-semester credit limit. Reuses program / semester / academic session.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UnivRegistrationPeriod(models.Model):
    _name = "univ.registration.period"
    _description = "Course Registration Period"
    _inherit = ["mail.thread"]
    _order = "open_datetime desc, id desc"

    name = fields.Char(string="Name", required=True, tracking=True)
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    semester_id = fields.Many2one(
        comodel_name="univ.semester",
        string="Semester",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    session_id = fields.Many2one(
        comodel_name="univ.academic.session",
        string="Academic Session",
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    open_datetime = fields.Datetime(
        string="Registration Opens", required=True, tracking=True
    )
    close_datetime = fields.Datetime(
        string="Registration Closes", required=True, tracking=True
    )
    credit_limit = fields.Float(
        string="Credit Limit",
        default=24.0,
        tracking=True,
        help="Maximum total credits a student may register in this period.",
    )
    active = fields.Boolean(string="Active", default=True)
    is_open = fields.Boolean(
        string="Open Now", compute="_compute_is_open"
    )
    status = fields.Selection(
        selection=[
            ("upcoming", "Upcoming"),
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        string="Status",
        compute="_compute_is_open",
    )
    offering_ids = fields.One2many(
        comodel_name="univ.course.offering",
        inverse_name="period_id",
        string="Course Offerings",
    )
    registration_ids = fields.One2many(
        comodel_name="univ.course.registration",
        inverse_name="period_id",
        string="Registrations",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="program_id.company_id",
        store=True,
        index=True,
    )

    @api.depends("open_datetime", "close_datetime", "active")
    def _compute_is_open(self):
        now = fields.Datetime.now()
        for period in self:
            opened = bool(period.open_datetime and period.open_datetime <= now)
            closed = bool(period.close_datetime and period.close_datetime < now)
            period.is_open = period.active and opened and not closed
            if not period.active or closed:
                period.status = "closed"
            elif opened:
                period.status = "open"
            else:
                period.status = "upcoming"

    @api.constrains("open_datetime", "close_datetime")
    def _check_window(self):
        for period in self:
            if (
                period.open_datetime
                and period.close_datetime
                and period.close_datetime < period.open_datetime
            ):
                raise ValidationError(
                    _(
                        "Registration close date cannot precede the open date."
                    )
                )

    def _ensure_open(self):
        """Raise a clear error if the window is not currently open."""
        self.ensure_one()
        if not self.is_open:
            raise UserError(
                _(
                    "The course registration window for %(name)s is not open. "
                    "Add/drop is only allowed between %(start)s and %(end)s.",
                    name=self.name,
                    start=self.open_datetime or "-",
                    end=self.close_datetime or "-",
                )
            )

    @api.model
    def _get_period_for_student(self, student):
        """Most relevant registration period for a student's program/semester:
        the open one if any, otherwise the latest."""
        if not student.program_id or not student.semester_id:
            return self.browse()
        periods = self.search(
            [
                ("program_id", "=", student.program_id.id),
                ("semester_id", "=", student.semester_id.id),
                ("active", "=", True),
            ]
        )
        open_periods = periods.filtered(lambda p: p.is_open)
        if open_periods:
            return open_periods[:1]
        return periods[:1]
