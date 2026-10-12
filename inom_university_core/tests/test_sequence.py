# -*- coding: utf-8 -*-
from odoo.tests.common import tagged
from .common import UniversityCommon


@tagged("post_install", "-at_install")
class TestSequence(UniversityCommon):

    def test_enrolment_no_generated(self):
        student = self._create_student(name="Sequence Student")
        self.assertTrue(student.enrolment_no, "Enrolment number should be auto-generated")

    def test_enrolment_no_uses_campus_prefix(self):
        self.company.univ_student_prefix = "CAMP"
        student = self._create_student(name="Prefix Student")
        self.assertTrue(
            student.enrolment_no.startswith("CAMP/"),
            "Enrolment number should use the campus prefix",
        )

    def test_enrolment_no_unique_increment(self):
        s1 = self._create_student(name="Student One")
        s2 = self._create_student(name="Student Two")
        self.assertNotEqual(
            s1.enrolment_no, s2.enrolment_no,
            "Each student must receive a distinct enrolment number",
        )

    def test_faculty_code_generated(self):
        faculty = self.env["univ.faculty"].create(
            {
                "name": "Test Faculty",
                "department_id": self.department.id,
                "designation": "lecturer",
            }
        )
        self.assertTrue(faculty.code, "Faculty code should be auto-generated")

    def test_student_partner_created(self):
        student = self._create_student(name="Partner Student")
        self.assertTrue(student.partner_id, "A related partner should be created")
        self.assertTrue(student.partner_id.is_univ_student)
