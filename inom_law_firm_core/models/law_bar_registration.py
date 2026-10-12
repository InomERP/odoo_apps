# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class LawBarRegistration(models.Model):
    _name = "law.bar.registration"
    _description = "Bar Registration / License"
    _order = "expiry_date, id"

    name = fields.Char(string="Registration / License No.", required=True)
    employee_id = fields.Many2one("hr.employee", string="Lawyer", required=True, ondelete="cascade")
    bar_council = fields.Char(string="Bar Council / Authority")
    registration_date = fields.Date()
    expiry_date = fields.Date()
    # Not stored: computed on read so the status always reflects the current date
    # without needing a manual write or a scheduled recompute.
    state = fields.Selection(
        [("valid", "Valid"), ("expired", "Expired")],
        string="Status", compute="_compute_state", search="_search_state",
    )
    active = fields.Boolean(default=True)

    @api.depends("expiry_date")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.state = "expired" if rec.expiry_date and rec.expiry_date < today else "valid"

    def _search_state(self, operator, value):
        if operator not in ("=", "!="):
            raise NotImplementedError(_("Unsupported operator for status search."))
        today = fields.Date.context_today(self)
        expired_domain = ["&", ("expiry_date", "!=", False), ("expiry_date", "<", today)]
        valid_domain = ["|", ("expiry_date", "=", False), ("expiry_date", ">=", today)]
        want_expired = (operator == "=" and value == "expired") or \
                       (operator == "!=" and value == "valid")
        return expired_domain if want_expired else valid_domain
