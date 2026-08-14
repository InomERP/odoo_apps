# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    is_lawyer = fields.Boolean(string="Legal Staff", default=False, index=True)
    lawyer_role = fields.Selection(
        [
            ("managing_partner", "Managing Partner"),
            ("senior_partner", "Senior Partner"),
            ("partner", "Partner"),
            ("senior_lawyer", "Senior Lawyer"),
            ("lawyer", "Lawyer"),
            ("junior_lawyer", "Junior Lawyer"),
            ("advocate", "Advocate"),
            ("paralegal", "Paralegal"),
            ("legal_assistant", "Legal Assistant"),
            ("legal_clerk", "Legal Clerk"),
        ],
        string="Legal Role",
    )
    specialization_ids = fields.Many2many("law.specialization", string="Specializations")
    bar_registration_ids = fields.One2many("law.bar.registration", "employee_id",
                                           string="Bar Registrations")
    billing_rate = fields.Float(
        string="Hourly Billing Rate",
        help="Default hourly billing rate; propagates to timesheet lines in Phase 15.",
    )
    law_availability = fields.Selection(
        [("available", "Available"), ("busy", "Busy"), ("unavailable", "Unavailable")],
        string="Availability", default="available",
    )
