# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from .common import UniversityCommon


@tagged("post_install", "-at_install")
class TestStudentWorkflow(UniversityCommon):

    def _add_primary_guardian(self, student):
        return self.env["univ.student.guardian"].create(
            {
                "name": "Guardian",
                "student_id": student.id,
                "relationship": "father",
                "is_primary": True,
            }
        )

    def _add_verified_document(self, student):
        doc = self.env["univ.student.document"].create(
            {
                "name": "10th Marksheet",
                "student_id": student.id,
                "doc_type": "tenth",
                "file_name": "tenth.png",
                "file": b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0"
                        b"lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            }
        )
        doc.action_verify()
        return doc

    def test_initial_state_is_draft(self):
        student = self._create_student()
        self.assertEqual(student.state, "draft")

    def test_enroll_transition(self):
        student = self._create_student()
        student.action_enroll()
        self.assertEqual(student.state, "enrolled")

    def test_activation_blocked_without_guardian_and_docs(self):
        student = self._create_student()
        student.action_enroll()
        with self.assertRaises(UserError):
            student.action_activate()

    def test_activation_succeeds_when_requirements_met(self):
        student = self._create_student()
        self._add_primary_guardian(student)
        self._add_verified_document(student)
        student.action_enroll()
        student.action_activate()
        self.assertEqual(student.state, "active")

    def test_graduate_and_drop(self):
        student = self._create_student()
        self._add_primary_guardian(student)
        self._add_verified_document(student)
        student.action_enroll()
        student.action_activate()
        student.action_graduate()
        self.assertEqual(student.state, "graduated")

    def test_document_complete_flag(self):
        student = self._create_student()
        doc = self._add_verified_document(student)
        self.assertTrue(student.document_complete)
        doc.action_reject()
        self.assertFalse(student.document_complete)

    def test_single_primary_guardian_enforced(self):
        student = self._create_student()
        self._add_primary_guardian(student)
        with self.assertRaises(Exception):
            self.env["univ.student.guardian"].create(
                {
                    "name": "Second Primary",
                    "student_id": student.id,
                    "relationship": "mother",
                    "is_primary": True,
                }
            )
