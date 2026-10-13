# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCampus(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env["univ.program"].create({"name": "P", "code": "P"})
        cls.batch = cls.env["univ.batch"].create({"name": "B", "code": "B", "program_id": cls.program.id})
        cls.sem = cls.env["univ.semester"].create({"name": "S", "code": "S", "program_id": cls.program.id})
        cls.student = cls.env["univ.student"].create({
            "name": "A", "program_id": cls.program.id, "batch_id": cls.batch.id,
            "semester_id": cls.sem.id, "state": "active"})

    def test_aggregates_compute(self):
        data = self.student.get_campus_dashboard()
        self.assertEqual(data["library_count"], 0)
        self.assertEqual(data["pending_assignments"], 0)
        self.assertIn("outstanding", data)
