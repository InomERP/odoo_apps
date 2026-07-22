# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivFaculty(models.Model):
    _inherit = "univ.faculty"

    session_ids = fields.One2many(
        comodel_name="univ.timetable.session", inverse_name="faculty_id",
        string="Timetable Sessions",
    )
    weekly_session_count = fields.Integer(
        string="Weekly Sessions", compute="_compute_workload",
    )
    user_id = fields.Many2one(
        comodel_name="res.users", string="Portal/Login User",
        compute="_compute_user_id",
        help="Resolved from the faculty contact, used for faculty portal access.",
    )

    def _compute_workload(self):
        for faculty in self:
            faculty.weekly_session_count = len(
                faculty.session_ids.filtered(lambda s: s.state == "confirmed")
            )

    @api.depends("partner_id")
    def _compute_user_id(self):
        for faculty in self:
            user = self.env["res.users"].search(
                [("partner_id", "=", faculty.partner_id.id)], limit=1
            ) if faculty.partner_id else self.env["res.users"]
            faculty.user_id = user.id
