# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class UnivExamSeatWizard(models.TransientModel):
    _name = "univ.exam.seat.wizard"
    _description = "Seat Allocation"

    schedule_id = fields.Many2one(
        comodel_name="univ.exam.schedule", string="Exam Schedule", required=True,
    )
    room_ids = fields.Many2many(
        comodel_name="univ.room", string="Halls", required=True,
    )

    def action_allocate(self):
        """Capacity-aware seat allocation across the selected halls."""
        self.ensure_one()
        students = self.schedule_id._eligible_students()
        if not students:
            raise UserError(_("No eligible students for this exam."))
        rooms = list(self.room_ids)
        if not rooms:
            raise UserError(_("Select at least one hall."))
        self.schedule_id.seat_ids.unlink()
        Seat = self.env["univ.exam.seat"]
        room_idx, seat_no = 0, 1
        for student in students:
            room = rooms[room_idx]
            if seat_no > (room.capacity or len(students)):
                room_idx += 1
                seat_no = 1
                if room_idx >= len(rooms):
                    raise UserError(_(
                        "Halls are full. Add more capacity."
                    ))
                room = rooms[room_idx]
            Seat.create({
                "schedule_id": self.schedule_id.id,
                "student_id": student.id,
                "room_id": room.id,
                "seat_no": str(seat_no),
            })
            seat_no += 1
        return {
            "type": "ir.actions.act_window",
            "res_model": "univ.exam.seat",
            "view_mode": "list",
            "domain": [("schedule_id", "=", self.schedule_id.id)],
        }
