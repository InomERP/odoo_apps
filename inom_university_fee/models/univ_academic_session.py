# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivAcademicSession(models.Model):
    _name = "univ.academic.session"
    _description = "Academic Session"
    _order = "start_date desc, name"

    name = fields.Char(string="Academic Session", required=True,
                       help="e.g. 2024-2025")
    code = fields.Char(string="Code")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    is_current = fields.Boolean(string="Current Session")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True,
    )

    _sql_constraints = [
        ("code_uniq", "unique(code, company_id)",
         "The session code must be unique per company."),
    ]

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and \
                    record.end_date < record.start_date:
                raise ValidationError(
                    _("End date cannot be before the start date.")
                )
