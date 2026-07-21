# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import AdmissionCommon


@tagged("post_install", "-at_install")
class TestDocumentWorkflow(AdmissionCommon):
    def _assign(self, applicant, template_ref):
        template = self.env.ref(template_ref)
        wizard = self.env["univ.assign.documents.wizard"].create(
            {"applicant_id": applicant.id, "template_id": template.id}
        )
        wizard._onchange_template_id()
        wizard.action_assign()
        return applicant.document_ids

    def test_assign_creates_draft_requirements(self):
        applicant = self._make_applicant()
        docs = self._assign(
            applicant, "inom_university_admission.req_template_indian"
        )
        self.assertEqual(len(docs), 4)
        self.assertTrue(all(d.state == "draft" for d in docs))
        self.assertFalse(any(d.file for d in docs))

    def test_assign_no_duplicates(self):
        applicant = self._make_applicant()
        self._assign(applicant, "inom_university_admission.req_template_indian")
        # Re-applying the same template must not duplicate rows.
        self._assign(applicant, "inom_university_admission.req_template_indian")
        types = applicant.document_ids.mapped("doc_type")
        self.assertEqual(len(types), len(set(types)))

    @mute_logger("odoo.sql_db")
    def test_unique_constraint(self):
        applicant = self._make_applicant()
        self.env["univ.applicant.document"].create(
            {"applicant_id": applicant.id, "doc_type": "tenth"}
        )
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["univ.applicant.document"].create(
                    {"applicant_id": applicant.id, "doc_type": "tenth"}
                )

    def test_portal_submit_draft_to_submitted(self):
        applicant = self._make_applicant()
        doc = self.env["univ.applicant.document"].create(
            {"applicant_id": applicant.id, "doc_type": "tenth"}
        )
        self.assertEqual(doc.state, "draft")
        doc.portal_submit(b"ZmFrZQ==", "tenth.pdf")
        self.assertEqual(doc.state, "submitted")
        self.assertTrue(doc.file)

    def test_locked_document_cannot_be_replaced(self):
        applicant = self._make_applicant()
        doc = self.env["univ.applicant.document"].create(
            {"applicant_id": applicant.id, "doc_type": "tenth"}
        )
        doc.portal_submit(b"ZmFrZQ==", "tenth.pdf")  # submitted (locked)
        with self.assertRaises(UserError):
            doc.portal_submit(b"b3RoZXI=", "other.pdf")

    def test_rejected_replace_resets_and_bumps_revision(self):
        applicant = self._make_applicant()
        doc = self.env["univ.applicant.document"].create(
            {"applicant_id": applicant.id, "doc_type": "tenth"}
        )
        doc.portal_submit(b"ZmFrZQ==", "tenth.pdf")
        doc.reject_reason = "Blurry scan"
        doc.action_reject()
        self.assertEqual(doc.state, "rejected")
        doc.portal_submit(b"bmV3ZmlsZQ==", "tenth_v2.pdf")
        self.assertEqual(doc.state, "submitted")
        self.assertFalse(doc.reject_reason)
        self.assertEqual(doc.version, 2)

    def test_completeness_uses_mandatory(self):
        applicant = self._make_applicant()
        mand = self.env["univ.applicant.document"].create(
            {"applicant_id": applicant.id, "doc_type": "tenth", "mandatory": True}
        )
        self.env["univ.applicant.document"].create(
            {"applicant_id": applicant.id, "doc_type": "other", "mandatory": False}
        )
        mand.portal_submit(b"ZmFrZQ==", "tenth.pdf")
        mand.action_verify()
        # Mandatory verified -> complete, even though the optional one is draft.
        self.assertTrue(applicant.document_complete)
