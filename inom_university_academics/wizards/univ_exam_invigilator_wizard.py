# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivExamInvigilatorWizard(models.TransientModel):
    _name = "univ.exam.invigilator.wizard"
    _description = "Assign Invigilators"

    schedule_id = fields.Many2one(
        comodel_name="univ.exam.schedule", string="Exam Schedule", required=True,
    )
    faculty_ids = fields.Many2many(
        comodel_name="univ.faculty", string="Invigilators", required=True,
    )

    def action_assign(self):
        self.ensure_one()
        Inv = self.env["univ.exam.invigilator"]
        existing = self.schedule_id.invigilator_ids.mapped("faculty_id")
        for faculty in self.faculty_ids:
            if faculty not in existing:
                Inv.create({
                    "schedule_id": self.schedule_id.id,
                    "faculty_id": faculty.id,
                })
        return {"type": "ir.actions.act_window_close"}
