# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLms(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env["univ.program"].create({"name": "P", "code": "P"})
        cls.batch = cls.env["univ.batch"].create({"name": "B", "code": "B", "program_id": cls.program.id})
        cls.sem = cls.env["univ.semester"].create({"name": "S", "code": "S", "program_id": cls.program.id})
        cls.subject = cls.env["univ.subject"].create({"name": "Sub", "code": "SUB", "program_id": cls.program.id})
        cls.student = cls.env["univ.student"].create({"name": "A", "program_id": cls.program.id, "batch_id": cls.batch.id, "semester_id": cls.sem.id, "state": "active"})
        cls.assignment = cls.env["univ.assignment"].create({
            "name": "A1", "subject_id": cls.subject.id,
            "due_date": fields.Datetime.now() + timedelta(days=2), "max_marks": 100, "allow_late": False})

    def test_submission_grade(self):
        sub = self.env["univ.assignment.submission"].create({
            "assignment_id": self.assignment.id, "student_id": self.student.id})
        self.assertFalse(sub.is_late)
        sub.write({"grade": 80})
        sub.action_grade()
        self.assertEqual(sub.state, "graded")

    def test_grade_out_of_range(self):
        sub = self.env["univ.assignment.submission"].create({
            "assignment_id": self.assignment.id, "student_id": self.student.id})
        with self.assertRaises(ValidationError):
            sub.write({"grade": 200})
