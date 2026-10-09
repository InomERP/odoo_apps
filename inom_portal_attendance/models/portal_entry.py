# -*- coding: utf-8 -*-
from odoo import models


class PortalEntry(models.Model):
    _inherit = "portal.entry"

    def _filter_visible_portal_cards(self):
        """Apply the attendance feature/user eligibility rule to its portal card."""
        visible = super()._filter_visible_portal_cards()
        attendance_entry = self.filtered(lambda entry: entry.url == "/my/attendance")
        # The base implementation treats every config card as visible, so remove
        # this card first and add it back only for enabled, employee-linked users.
        visible -= attendance_entry
        if attendance_entry:
            params = self.env["ir.config_parameter"].sudo()
            enabled = params.get_str("inom_portal_attendance.enabled") in ("True", "true", "1")
            employee = self.env["hr.employee"].sudo().search(
                [("user_id", "=", self.env.user.id)], limit=1
            )
            if enabled and employee:
                visible |= attendance_entry
        return visible
