# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class AdmissionCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.faculty_school = cls.env["univ.faculty_school"].create(
            {"name": "School of Engineering", "code": "SOE"}
        )
        cls.department = cls.env["univ.department"].create(
            {
                "name": "Computer Science",
                "code": "CSE",
                "faculty_school_id": cls.faculty_school.id,
            }
        )
        cls.program = cls.env["univ.program"].create(
            {
                "name": "B.Tech CSE",
                "code": "BT-CSE",
                "department_id": cls.department.id,
            }
        )
        cls.batch = cls.env["univ.batch"].create(
            {"name": "2026", "code": "B26", "program_id": cls.program.id, "start_year": 2026}
        )
        cls.section = cls.env["univ.section"].create(
            {
                "name": "A",
                "code": "SEC-A",
                "program_id": cls.program.id,
                "batch_id": cls.batch.id,
                "capacity": 60,
            }
        )
        cls.admission_round = cls.env["univ.admission.round"].create(
            {
                "name": "Fall 2026 R1",
                "code": "F26R1",
                "program_id": cls.program.id,
                "start_date": "2026-01-01",
                "end_date": "2026-06-30",
                "state": "open",
            }
        )
        cls.quota = cls.env.ref("inom_university_admission.quota_general")

    def _make_applicant(self, **kw):
        vals = {
            "name": "Test Applicant",
            "email": "test.applicant@example.com",
            "program_id": self.program.id,
            "round_id": self.admission_round.id,
            "quota_id": self.quota.id,
            "admission_fee": 1000.0,
        }
        vals.update(kw)
        return self.env["univ.applicant"].create(vals)

    def _verify_min_documents(self, applicant):
        doc = self.env["univ.applicant.document"].create(
            {
                "name": "10th",
                "applicant_id": applicant.id,
                "doc_type": "tenth",
                "file": b"ZmFrZQ==",
                "file_name": "tenth.pdf",
            }
        )
        doc.action_verify()
        return doc
