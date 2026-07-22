# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class UnivAttendanceBulkWizard(models.TransientModel):
    _name = "univ.attendance.bulk.wizard"
    _description = "Bulk Attendance Generator"

    date = fields.Date(string="Date", required=True,
                       default=fields.Date.context_today)
    section_id = fields.Many2one(comodel_name="univ.section", string="Section")
    faculty_id = fields.Many2one(comodel_name="univ.faculty", string="Faculty")
    mark_all_present = fields.Boolean(string="Mark All Present", default=True)

    def action_generate(self):
        """Create attendance sheets for all confirmed sessions matching filters."""
        self.ensure_one()
        domain = [("date", "=", self.date), ("state", "=", "confirmed")]
        if self.section_id:
            domain.append(("section_id", "=", self.section_id.id))
        if self.faculty_id:
            domain.append(("faculty_id", "=", self.faculty_id.id))
        sessions = self.env["univ.timetable.session"].search(domain)
        if not sessions:
            raise UserError(_("No confirmed sessions match the filters."))
        Sheet = self.env["univ.attendance.sheet"]
        sheets = Sheet
        for session in sessions:
            sheet = Sheet.search([("session_id", "=", session.id)], limit=1)
            if not sheet:
                sheet = Sheet.create({"session_id": session.id})
            sheet.action_generate_lines()
            if self.mark_all_present:
                sheet.action_mark_all_present()
            sheets |= sheet
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendance Sheets"),
            "res_model": "univ.attendance.sheet",
            "view_mode": "list,form",
            "domain": [("id", "in", sheets.ids)],
        }
