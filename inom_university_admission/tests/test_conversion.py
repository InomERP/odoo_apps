# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import AdmissionCommon


@tagged("post_install", "-at_install")
class TestConversion(AdmissionCommon):
    def _drive_to_ready(self, applicant):
        self._verify_min_documents(applicant)
        applicant.action_issue_offer()
        applicant.action_accept_offer()
        applicant.action_mark_fee_paid()

    def test_enrol_requires_offer_and_fee(self):
        applicant = self._make_applicant()
        with self.assertRaises(UserError):
            applicant.action_enrol_to_student()

    def test_enrol_creates_student(self):
        applicant = self._make_applicant()
        self._drive_to_ready(applicant)
        applicant.action_enrol_to_student()
        self.assertTrue(applicant.student_id)
        self.assertTrue(applicant.is_enrolled)
        self.assertTrue(applicant.stage_id.is_won)

    def test_student_inherits_profile(self):
        applicant = self._make_applicant(gender="male", category="general")
        self._drive_to_ready(applicant)
        applicant.action_enrol_to_student()
        student = applicant.student_id
        self.assertEqual(student.name, applicant.name)
        self.assertEqual(student.program_id, applicant.program_id)

    def test_section_allocated(self):
        applicant = self._make_applicant()
        self._drive_to_ready(applicant)
        applicant.action_enrol_to_student()
        self.assertEqual(applicant.student_id.section_id, self.section)

    def test_documents_copied(self):
        applicant = self._make_applicant()
        self._drive_to_ready(applicant)
        applicant.action_enrol_to_student()
        self.assertTrue(applicant.student_id.document_ids)

    def test_enrolled_cannot_be_deleted(self):
        applicant = self._make_applicant()
        self._drive_to_ready(applicant)
        applicant.action_enrol_to_student()
        demo_user = self.env["res.users"].create(
            {
                "name": "Officer",
                "login": "officer_test",
                "groups_id": [
                    (
                        4,
                        self.env.ref(
                            "inom_university_admission.group_univ_admission_officer"
                        ).id,
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            applicant.with_user(demo_user).unlink()
