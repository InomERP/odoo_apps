# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UnivHostel(models.Model):
    _name = "univ.hostel"
    _description = "Hostel"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(string="Hostel", required=True)
    code = fields.Char(string="Code")
    hostel_type = fields.Selection(
        selection=[("boys", "Boys"), ("girls", "Girls"), ("mixed", "Mixed")],
        string="Type", default="boys", required=True)
    warden_id = fields.Many2one(comodel_name="univ.faculty", string="Warden",
                                tracking=True)
    block_ids = fields.One2many(comodel_name="univ.hostel.block",
                                inverse_name="hostel_id", string="Blocks")
    block_count = fields.Integer(string="Blocks", compute="_compute_counts")
    bed_count = fields.Integer(string="Beds", compute="_compute_counts")
    occupied_count = fields.Integer(string="Occupied", compute="_compute_counts")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        default=lambda self: self.env.company, index=True)

    def _compute_counts(self):
        Bed = self.env["univ.hostel.bed"]
        for hostel in self:
            hostel.block_count = len(hostel.block_ids)
            beds = Bed.search([("hostel_id", "=", hostel.id)])
            hostel.bed_count = len(beds)
            hostel.occupied_count = len(beds.filtered(
                lambda b: b.state == "occupied"))


class UnivHostelBlock(models.Model):
    _name = "univ.hostel.block"
    _description = "Hostel Block"
    _order = "hostel_id, name"

    name = fields.Char(string="Block", required=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel",
                                required=True, ondelete="cascade", index=True)
    floor_ids = fields.One2many(comodel_name="univ.hostel.floor",
                                inverse_name="block_id", string="Floors")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="hostel_id.company_id", store=True, index=True)


class UnivHostelFloor(models.Model):
    _name = "univ.hostel.floor"
    _description = "Hostel Floor"
    _order = "block_id, sequence"

    name = fields.Char(string="Floor", required=True)
    sequence = fields.Integer(default=10)
    block_id = fields.Many2one(comodel_name="univ.hostel.block", string="Block",
                               required=True, ondelete="cascade", index=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel",
                                related="block_id.hostel_id", store=True)
    room_ids = fields.One2many(comodel_name="univ.hostel.room",
                               inverse_name="floor_id", string="Rooms")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="block_id.company_id", store=True, index=True)


class UnivHostelRoom(models.Model):
    _name = "univ.hostel.room"
    _description = "Hostel Room"
    _order = "floor_id, room_no"

    name = fields.Char(string="Room", compute="_compute_name", store=True)
    room_no = fields.Char(string="Room No.", required=True)
    floor_id = fields.Many2one(comodel_name="univ.hostel.floor", string="Floor",
                               required=True, ondelete="cascade", index=True)
    block_id = fields.Many2one(comodel_name="univ.hostel.block", string="Block",
                               related="floor_id.block_id", store=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel",
                                related="floor_id.hostel_id", store=True, index=True)
    capacity = fields.Integer(string="Capacity", default=2, required=True)
    bed_ids = fields.One2many(comodel_name="univ.hostel.bed",
                              inverse_name="room_id", string="Beds")
    occupied = fields.Integer(string="Occupied", compute="_compute_occupancy")
    available = fields.Integer(string="Available", compute="_compute_occupancy")
    occupancy_rate = fields.Float(string="Occupancy %",
                                  compute="_compute_occupancy")
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="floor_id.company_id", store=True, index=True)

    @api.depends("room_no", "hostel_id")
    def _compute_name(self):
        for room in self:
            room.name = "%s / %s" % (room.hostel_id.name or "", room.room_no or "")

    @api.depends("bed_ids.state", "capacity")
    def _compute_occupancy(self):
        for room in self:
            occ = len(room.bed_ids.filtered(lambda b: b.state == "occupied"))
            room.occupied = occ
            room.available = max(len(room.bed_ids) - occ, 0)
            room.occupancy_rate = (occ / len(room.bed_ids) * 100.0) \
                if room.bed_ids else 0.0

    def action_generate_beds(self):
        """Create beds up to the room capacity."""
        Bed = self.env["univ.hostel.bed"]
        for room in self:
            existing = len(room.bed_ids)
            for i in range(existing, room.capacity):
                Bed.create({"room_id": room.id, "bed_no": str(i + 1)})


class UnivHostelBed(models.Model):
    _name = "univ.hostel.bed"
    _description = "Hostel Bed"
    _order = "room_id, bed_no"

    name = fields.Char(string="Bed", compute="_compute_name", store=True)
    bed_no = fields.Char(string="Bed No.", required=True)
    room_id = fields.Many2one(comodel_name="univ.hostel.room", string="Room",
                              required=True, ondelete="cascade", index=True)
    hostel_id = fields.Many2one(comodel_name="univ.hostel", string="Hostel",
                                related="room_id.hostel_id", store=True, index=True)
    state = fields.Selection(
        selection=[("available", "Available"), ("occupied", "Occupied"),
                   ("blocked", "Blocked")],
        string="Status", default="available", required=True, index=True)
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company",
        related="room_id.company_id", store=True, index=True)

    @api.depends("room_id", "bed_no")
    def _compute_name(self):
        for bed in self:
            bed.name = "%s-%s" % (bed.room_id.name or "", bed.bed_no or "")
