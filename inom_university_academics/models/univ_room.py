# -*- coding: utf-8 -*-
from odoo import fields, models


class UnivRoom(models.Model):
    _name = "univ.room"
    _description = "Room / Classroom / Hall"
    _order = "name"

    name = fields.Char(string="Room", required=True)
    code = fields.Char(string="Code")
    room_type = fields.Selection(
        selection=[
            ("classroom", "Classroom"),
            ("lab", "Laboratory"),
            ("hall", "Exam Hall"),
            ("seminar", "Seminar Hall"),
        ],
        string="Type",
        default="classroom",
        required=True,
    )
    capacity = fields.Integer(string="Capacity", default=60)
    building = fields.Char(string="Building / Block")
    floor = fields.Char(string="Floor")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True,
    )

    _sql_constraints = [
        ("code_uniq", "unique(code, company_id)",
         "The room code must be unique per company."),
    ]
