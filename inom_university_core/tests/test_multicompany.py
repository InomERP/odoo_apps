# -*- coding: utf-8 -*-
from odoo.tests.common import tagged
from .common import UniversityCommon


@tagged("post_install", "-at_install")
class TestMultiCompany(UniversityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env["res.company"].create({"name": "Campus B"})

    def test_company_b_student_hidden_from_company_a_user(self):
        # Student belonging to Campus B
        school_b = self.env["univ.faculty_school"].create(
            {"name": "School B", "code": "SB", "company_id": self.company_b.id}
        )
        dept_b = self.env["univ.department"].create(
            {
                "name": "Dept B",
                "code": "DB",
                "faculty_school_id": school_b.id,
            }
        )
        program_b = self.env["univ.program"].create(
            {
                "name": "Program B",
                "code": "PB",
                "department_id": dept_b.id,
                "company_id": self.company_b.id,
            }
        )
        student_b = self.env["univ.student"].create(
            {
                "name": "Campus B Student",
                "program_id": program_b.id,
                "company_id": self.company_b.id,
            }
        )

        # User restricted to Campus A only
        user_a = self.env["res.users"].create(
            {
                "name": "Campus A User",
                "login": "campus_a_user",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "groups_id": [
                    (6, 0, [self.env.ref("inom_university_core.group_univ_registrar").id])
                ],
            }
        )

        visible = (
            self.env["univ.student"]
            .with_user(user_a)
            .search([("id", "=", student_b.id)])
        )
        self.assertFalse(
            visible,
            "Campus A user must not see Campus B student records",
        )
