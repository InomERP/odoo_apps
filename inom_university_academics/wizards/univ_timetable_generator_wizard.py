# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class UnivTimetableGeneratorWizard(models.TransientModel):
    _name = "univ.timetable.generator.wizard"
    _description = "Timetable Generator"

    section_id = fields.Many2one(
        comodel_name="univ.section", string="Section", required=True,
    )
    date_from = fields.Date(string="From", required=True,
                            default=fields.Date.context_today)
    date_to = fields.Date(string="To", required=True)
    slot_ids = fields.Many2many(
        comodel_name="univ.timeslot", string="Slots",
        domain="[('is_break', '=', False)]",
    )
    subject_ids = fields.Many2many(
        comodel_name="univ.subject", string="Subjects",
    )
    confirm_sessions = fields.Boolean(string="Confirm Sessions", default=True)

    @api.onchange("section_id")
    def _onchange_section(self):
        if self.section_id:
            self.subject_ids = self.env["univ.subject"].search([
                ("program_id", "=", self.section_id.program_id.id),
                ("semester_id", "=", self.section_id.semester_id.id),
            ])
            self.slot_ids = self.env["univ.timeslot"].search(
                [("is_break", "=", False)]
            )

    def _faculty_for(self, subject):
        return subject.faculty_ids[:1]

    def action_generate(self):
        """Greedy, clash-free allocation: round-robin subjects across slots/days.

        Hard constraints (faculty/room/section uniqueness per slot/date) are
        enforced by the session model's constraint; the generator skips any
        placement that would clash and continues.
        """
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(self.env._("End date must be after start date."))
        if not self.subject_ids or not self.slot_ids:
            raise UserError(self.env._("Select subjects and slots."))
        Session = self.env["univ.timetable.session"]
        subjects = list(self.subject_ids)
        created = Session
        subj_index = 0
        day = self.date_from
        while day <= self.date_to:
            if day.weekday() == 6:  # skip Sunday
                day += timedelta(days=1)
                continue
            for slot in self.slot_ids.sorted("sequence"):
                subject = subjects[subj_index % len(subjects)]
                subj_index += 1
                faculty = self._faculty_for(subject)
                if not faculty:
                    continue
                try:
                    session = Session.create({
                        "section_id": self.section_id.id,
                        "subject_id": subject.id,
                        "faculty_id": faculty.id,
                        "slot_id": slot.id,
                        "date": day,
                        "state": "confirmed" if self.confirm_sessions else "draft",
                    })
                    created |= session
                except Exception:
                    # Clash or validation: skip this placement.
                    continue
            day += timedelta(days=1)
        if not created:
            raise UserError(self.env._(
                "No sessions could be generated (check subjects have faculty)."
            ))
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Generated Sessions"),
            "res_model": "univ.timetable.session",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }
