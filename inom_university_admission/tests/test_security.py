# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from .common import AdmissionCommon


@tagged("post_install", "-at_install")
class TestSecurity(AdmissionCommon):
    def setUp(self):
        super().setUp()
        self.reviewer = self.env["res.users"].create(
            {
                "name": "Reviewer",
                "login": "reviewer_test",
                "group_ids": [
                    (
                        4,
                        self.env.ref(
                            "inom_university_admission.group_univ_admission_reviewer"
                        ).id,
                    )
                ],
            }
        )

    def test_reviewer_cannot_create_applicant(self):
        with self.assertRaises(AccessError):
            self.env["univ.applicant"].with_user(self.reviewer).create(
                {
                    "name": "Blocked",
                    "program_id": self.program.id,
                    "round_id": self.admission_round.id,
                }
            )

    def test_reviewer_can_read_applicant(self):
        applicant = self._make_applicant()
        # Should not raise.
        applicant.with_user(self.reviewer).read(["name"])

    def test_reviewer_can_verify_document(self):
        applicant = self._make_applicant()
        doc = self.env["univ.applicant.document"].create(
            {
                "name": "10th",
                "applicant_id": applicant.id,
                "doc_type": "tenth",
                "file": b"ZmFrZQ==",
                "file_name": "tenth.pdf",
            }
        )
        doc.with_user(self.reviewer).action_verify()
        self.assertEqual(doc.state, "verified")
