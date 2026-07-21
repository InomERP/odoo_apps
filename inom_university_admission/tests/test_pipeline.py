# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import AdmissionCommon


@tagged("post_install", "-at_install")
class TestPipeline(AdmissionCommon):
    def test_application_number_generated(self):
        applicant = self._make_applicant()
        self.assertTrue(applicant.application_no)
        self.assertNotEqual(applicant.application_no, "New")

    def test_partner_auto_created(self):
        applicant = self._make_applicant()
        self.assertTrue(applicant.partner_id)
        self.assertTrue(applicant.partner_id.is_univ_applicant)

    def test_default_stage(self):
        applicant = self._make_applicant()
        self.assertTrue(applicant.stage_id.is_default)

    def test_documents_verified_blocks_without_docs(self):
        applicant = self._make_applicant()
        applicant.action_start_verification()
        with self.assertRaises(UserError):
            applicant.action_documents_verified()

    def test_document_progress(self):
        applicant = self._make_applicant()
        self._verify_min_documents(applicant)
        self.assertEqual(applicant.document_progress, 100.0)
        self.assertTrue(applicant.document_complete)

    def test_issue_and_accept_offer(self):
        applicant = self._make_applicant()
        applicant.action_issue_offer()
        self.assertEqual(applicant.offer_state, "sent")
        applicant.action_accept_offer()
        self.assertEqual(applicant.offer_state, "accepted")
        self.assertEqual(applicant.fee_state, "pending")

    def test_reject_moves_to_rejected_stage(self):
        applicant = self._make_applicant()
        applicant._do_reject("Incomplete profile")
        self.assertTrue(applicant.stage_id.is_rejected)
        self.assertEqual(applicant.reject_reason, "Incomplete profile")

    def test_merit_score_weighted(self):
        applicant = self._make_applicant()
        self.env["univ.applicant.merit"].create(
            {
                "applicant_id": applicant.id,
                "source": "entrance_exam",
                "score": 80.0,
                "max_score": 100.0,
                "weight": 50.0,
            }
        )
        self.assertAlmostEqual(applicant.merit_score, 40.0)
