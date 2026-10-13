# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHostel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env["univ.program"].create({"name": "P", "code": "P"})
        cls.batch = cls.env["univ.batch"].create({"name": "B", "code": "B", "program_id": cls.program.id})
        cls.sem = cls.env["univ.semester"].create({"name": "S", "code": "S", "program_id": cls.program.id})
        cls.s1 = cls.env["univ.student"].create({"name": "A", "program_id": cls.program.id, "batch_id": cls.batch.id, "semester_id": cls.sem.id, "state": "active"})
        cls.s2 = cls.env["univ.student"].create({"name": "B", "program_id": cls.program.id, "batch_id": cls.batch.id, "semester_id": cls.sem.id, "state": "active"})
        cls.hostel = cls.env["univ.hostel"].create({"name": "H", "hostel_type": "boys"})
        cls.block = cls.env["univ.hostel.block"].create({"name": "BL", "hostel_id": cls.hostel.id})
        cls.floor = cls.env["univ.hostel.floor"].create({"name": "F", "block_id": cls.block.id})
        cls.room = cls.env["univ.hostel.room"].create({"room_no": "1", "floor_id": cls.floor.id, "capacity": 1})
        cls.bed = cls.env["univ.hostel.bed"].create({"bed_no": "1", "room_id": cls.room.id})

    def test_bed_double_allot_blocked(self):
        a1 = self.env["univ.hostel.allotment"].create({
            "student_id": self.s1.id, "hostel_id": self.hostel.id,
            "bed_id": self.bed.id, "state": "allotted"})
        with self.assertRaises(ValidationError):
            self.env["univ.hostel.allotment"].create({
                "student_id": self.s2.id, "hostel_id": self.hostel.id,
                "bed_id": self.bed.id, "state": "allotted"})
