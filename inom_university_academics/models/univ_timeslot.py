# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UnivTimeslot(models.Model):
    _name = "univ.timeslot"
    _description = "Timetable Period / Slot"
    _order = "sequence, start_time"

    name = fields.Char(string="Slot", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    start_time = fields.Float(string="Start Time", required=True,
                              help="Hour of day in 24h decimal, e.g. 9.5 = 09:30.")
    end_time = fields.Float(string="End Time", required=True)
    is_break = fields.Boolean(string="Break / Lunch",
                              help="Break slots are excluded from allocation.")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True,
    )

    @api.constrains("start_time", "end_time")
    def _check_times(self):
        for record in self:
            if not (0 <= record.start_time < 24) or not (0 < record.end_time <= 24):
                raise ValidationError(_("Times must be within 0-24."))
            if record.end_time <= record.start_time:
                raise ValidationError(
                    _("End time must be after start time.")
                )
