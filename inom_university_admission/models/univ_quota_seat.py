# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivQuotaSeat(models.Model):
    _name = "univ.quota.seat"
    _description = "Quota Seat Allocation"
    _order = "program_id, round_id, quota_id"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    program_id = fields.Many2one(
        comodel_name="univ.program",
        string="Program",
        required=True,
        ondelete="cascade",
        index=True,
    )
    quota_id = fields.Many2one(
        comodel_name="univ.quota",
        string="Quota",
        required=True,
        ondelete="restrict",
        index=True,
    )
    round_id = fields.Many2one(
        comodel_name="univ.admission.round",
        string="Round",
        required=True,
        ondelete="cascade",
        index=True,
    )
    capacity = fields.Integer(string="Capacity", default=0)
    used_seats = fields.Integer(
        string="Used", compute="_compute_seat_usage"
    )
    reserved_seats = fields.Integer(
        string="Offered/Reserved", compute="_compute_seat_usage"
    )
    available_seats = fields.Integer(
        string="Available", compute="_compute_seat_usage"
    )
    occupancy_rate = fields.Float(
        string="Occupancy %", compute="_compute_seat_usage"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Campus",
        related="round_id.company_id",
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            "quota_program_round_uniq",
            "unique(program_id, quota_id, round_id)",
            "A seat cap already exists for this program / quota / round.",
        ),
    ]

    @api.depends("program_id", "quota_id", "round_id")
    def _compute_name(self):
        for record in self:
            record.name = " / ".join(
                filter(
                    None,
                    [
                        record.program_id.code or record.program_id.name,
                        record.quota_id.code,
                        record.round_id.code,
                    ],
                )
            )

    def _compute_seat_usage(self):
        Applicant = self.env["univ.applicant"]
        for record in self:
            base_domain = [
                ("program_id", "=", record.program_id.id),
                ("quota_id", "=", record.quota_id.id),
                ("round_id", "=", record.round_id.id),
            ]
            used = Applicant.search_count(
                base_domain + [("stage_id.is_won", "=", True)]
            )
            reserved = Applicant.search_count(
                base_domain
                + [
                    ("offer_state", "in", ("sent", "accepted")),
                    ("stage_id.is_won", "=", False),
                ]
            )
            record.used_seats = used
            record.reserved_seats = reserved
            available = record.capacity - used - reserved
            record.available_seats = available
            record.occupancy_rate = (
                100.0 * (used + reserved) / record.capacity
                if record.capacity
                else 0.0
            )

    @api.constrains("capacity")
    def _check_capacity(self):
        for record in self:
            if record.capacity < 0:
                raise ValidationError(
                    _("Seat capacity cannot be negative.")
                )
