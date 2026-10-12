# -*- coding: utf-8 -*-
import base64
import csv
import io

from odoo import fields, models
from odoo.exceptions import UserError


class UnivMeritImportWizard(models.TransientModel):
    _name = "univ.merit.import.wizard"
    _description = "Bulk Merit / Entrance Import"

    round_id = fields.Many2one(
        comodel_name="univ.admission.round",
        string="Round",
        help="Optional filter to match applications inside one round.",
    )
    source = fields.Selection(
        selection=[
            ("entrance_exam", "Entrance Exam"),
            ("board_marks", "Board Marks"),
            ("interview", "Interview"),
            ("portfolio", "Portfolio"),
            ("other", "Other"),
        ],
        string="Score Source",
        default="entrance_exam",
        required=True,
    )
    max_score = fields.Float(string="Out Of", default=100.0)
    weight = fields.Float(string="Weight %", default=100.0)
    data_file = fields.Binary(string="CSV File", required=True)
    file_name = fields.Char(string="File Name")
    result_summary = fields.Text(string="Result", readonly=True)

    def action_import(self):
        """Import merit lines from a CSV with columns: application_no, score.

        An optional third column 'reference' is supported.
        """
        self.ensure_one()
        if not self.data_file:
            raise UserError(self.env._("Please attach a CSV file."))
        try:
            content = base64.b64decode(self.data_file).decode("utf-8-sig")
        except Exception as exc:  # noqa: BLE001
            raise UserError(
                self.env._("Unable to read the file as UTF-8 CSV: %s", exc)
            )
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise UserError(self.env._("The CSV file appears to be empty."))
        # Normalise header names.
        headers = {h.strip().lower(): h for h in reader.fieldnames}
        if "application_no" not in headers or "score" not in headers:
            raise UserError(
                self.env._(
                    "CSV must contain at least 'application_no' and 'score' "
                    "columns."
                )
            )
        Applicant = self.env["univ.applicant"]
        Merit = self.env["univ.applicant.merit"]
        imported = 0
        skipped = []
        for row in reader:
            app_no = (row.get(headers["application_no"]) or "").strip()
            raw_score = (row.get(headers["score"]) or "").strip()
            if not app_no:
                continue
            domain = [("application_no", "=", app_no)]
            if self.round_id:
                domain.append(("round_id", "=", self.round_id.id))
            applicant = Applicant.search(domain, limit=1)
            if not applicant:
                skipped.append(app_no)
                continue
            try:
                score = float(raw_score)
            except ValueError:
                skipped.append(app_no)
                continue
            reference = ""
            if "reference" in headers:
                reference = (row.get(headers["reference"]) or "").strip()
            Merit.create(
                {
                    "applicant_id": applicant.id,
                    "source": self.source,
                    "score": score,
                    "max_score": self.max_score,
                    "weight": self.weight,
                    "reference": reference,
                    "score_date": fields.Date.context_today(self),
                }
            )
            imported += 1
        summary = self.env._("Imported %(count)s merit lines.", count=imported)
        if skipped:
            summary += "\n" + self.env._(
                "Skipped (not found / invalid): %s", ", ".join(skipped)
            )
        self.result_summary = summary
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.merit.import.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
