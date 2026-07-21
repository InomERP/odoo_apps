# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UnivTimetableSubstitution(models.Model):
    _name = "univ.timetable.substitution"
    _description = "Timetable Substitution"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    session_id = fields.Many2one(
        comodel_name="univ.timetable.session", string="Session", required=True,
        ondelete="cascade", index=True, tracking=True,
    )
    date = fields.Date(string="Date", related="session_id.date", store=True)
    original_faculty_id = fields.Many2one(
        comodel_name="univ.faculty", string="Original Faculty",
        related="session_id.faculty_id", store=True,
    )
    substitute_faculty_id = fields.Many2one(
        comodel_name="univ.faculty", string="Substitute Faculty", required=True,
        tracking=True,
    )
    reason = fields.Text(string="Reason")
    state = fields.Selection(
        selection=[("draft", "Draft"), ("approved", "Approved"),
                   ("done", "Applied")],
        string="Status", default="draft", required=True, tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="session_id.company_id", store=True, index=True,
    )

    @api.constrains("substitute_faculty_id", "session_id")
    def _check_substitute(self):
        for record in self:
            if record.substitute_faculty_id == record.session_id.faculty_id:
                raise UserError(_(
                    "Substitute must differ from the original faculty."
                ))

    def action_approve(self):
        self.write({"state": "approved"})

    def action_apply(self):
        for record in self:
            if record.state != "approved":
                raise UserError(_("Approve the substitution first."))
            record.session_id.write({
                "faculty_id": record.substitute_faculty_id.id,
                "is_substituted": True,
            })
            record.state = "done"
