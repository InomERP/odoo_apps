# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLibrary(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env["univ.program"].create({"name": "P", "code": "P"})
        cls.batch = cls.env["univ.batch"].create({"name": "B", "code": "B", "program_id": cls.program.id})
        cls.sem = cls.env["univ.semester"].create({"name": "S1", "code": "S1", "program_id": cls.program.id})
        cls.student = cls.env["univ.student"].create({
            "name": "Stu", "program_id": cls.program.id, "batch_id": cls.batch.id,
            "semester_id": cls.sem.id, "state": "active"})
        cls.book = cls.env["univ.library.book"].create({"name": "Book"})
        cls.copy = cls.env["univ.library.copy"].create({"book_id": cls.book.id, "barcode": "BC1"})
        cls.member = cls.env["univ.library.member"].create({
            "member_type": "student", "student_id": cls.student.id, "max_books": 1})

    def test_issue_sets_copy_issued(self):
        issue = self.env["univ.library.issue"].create({
            "copy_id": self.copy.id, "member_id": self.member.id,
            "issue_date": fields.Date.today(), "due_date": fields.Date.today() + timedelta(days=14)})
        self.assertEqual(self.copy.state, "issued")
        issue.action_return()
        self.assertEqual(self.copy.state, "available")

    def test_limit_enforced(self):
        c2 = self.env["univ.library.copy"].create({"book_id": self.book.id, "barcode": "BC2"})
        self.env["univ.library.issue"].create({
            "copy_id": self.copy.id, "member_id": self.member.id,
            "issue_date": fields.Date.today(), "due_date": fields.Date.today() + timedelta(days=14)})
        with self.assertRaises(ValidationError):
            self.env["univ.library.issue"].create({
                "copy_id": c2.id, "member_id": self.member.id,
                "issue_date": fields.Date.today(), "due_date": fields.Date.today() + timedelta(days=14)})
