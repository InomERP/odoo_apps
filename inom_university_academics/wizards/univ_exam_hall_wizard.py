# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class UnivExamHallWizard(models.TransientModel):
    _name = "univ.exam.hall.wizard"
    _description = "Hall Allocation"

    schedule_id = fields.Many2one(
        comodel_name="univ.exam.schedule", string="Exam Schedule", required=True,
    )
    room_id = fields.Many2one(comodel_name="univ.room", string="Hall", required=True,
                              domain="[('room_type', '=', 'hall')]")

    def action_allocate(self):
        self.ensure_one()
        self.schedule_id.room_id = self.room_id.id
        return {"type": "ir.actions.act_window_close"}
