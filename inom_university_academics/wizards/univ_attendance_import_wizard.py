# -*- coding: utf-8 -*-
import base64
import csv
import io

from odoo import _, fields, models
from odoo.exceptions import UserError


class UnivAttendanceImportWizard(models.TransientModel):
    _name = "univ.attendance.import.wizard"
    _description = "Biometric Attendance Import"

    sheet_id = fields.Many2one(
        comodel_name="univ.attendance.sheet", string="Attendance Sheet",
        required=True,
    )
    data_file = fields.Binary(string="CSV File", required=True)
    filename = fields.Char(string="File Name")
    enrolment_column = fields.Char(
        string="Enrolment Column", default="enrolment_no",
        help="CSV header that holds the student enrolment number.",
    )
    status_column = fields.Char(
        string="Status Column", default="status",
        help="CSV header that holds present/absent/late/leave.",
    )

    def action_import(self):
        """Vendor-agnostic CSV importer with configurable column mapping."""
        self.ensure_one()
        self.sheet_id._ensure_editable()
        try:
            content = base64.b64decode(self.data_file).decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
        except Exception as exc:  # noqa: BLE001
            raise UserError(_("Could not read the CSV: %s", exc))
        status_map = {
            "p": "present", "present": "present", "1": "present",
            "a": "absent", "absent": "absent", "0": "absent",
            "l": "late", "late": "late",
            "leave": "leave",
        }
        lines_by_enrol = {
            line.student_id.enrolment_no: line
            for line in self.sheet_id.line_ids if line.student_id.enrolment_no
        }
        updated = 0
        for row in reader:
            enrol = (row.get(self.enrolment_column) or "").strip()
            raw = (row.get(self.status_column) or "").strip().lower()
            line = lines_by_enrol.get(enrol)
            if line and raw in status_map:
                line.state = status_map[raw]
                updated += 1
        if not updated:
            raise UserError(_(
                "No matching students were updated. Check column mapping."
            ))
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.attendance.sheet",
            "res_id": self.sheet_id.id,
            "view_mode": "form",
            "target": "current",
        }
