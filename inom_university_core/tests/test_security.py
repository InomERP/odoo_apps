# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from .common import UniversityCommon


@tagged("post_install", "-at_install")
class TestSecurity(UniversityCommon):

    def test_security_groups_exist(self):
        groups = [
            "inom_university_core.group_univ_admin",
            "inom_university_core.group_univ_registrar",
            "inom_university_core.group_univ_dean",
            "inom_university_core.group_univ_hod",
            "inom_university_core.group_univ_faculty",
            "inom_university_core.group_univ_portal_student",
            "inom_university_core.group_univ_portal_parent",
        ]
        for xmlid in groups:
            self.assertTrue(
                self.env.ref(xmlid, raise_if_not_found=False),
                "Missing security group: %s" % xmlid,
            )

    def test_faculty_user_cannot_delete_program(self):
        faculty_user = self.env["res.users"].create(
            {
                "name": "Faculty User",
                "login": "faculty_user_sec",
                "group_ids": [
                    (6, 0, [self.env.ref("inom_university_core.group_univ_faculty").id])
                ],
            }
        )
        program = self.env["univ.program"].with_user(faculty_user).browse(
            self.program.id
        )
        with self.assertRaises(AccessError):
            program.unlink()

    def test_registrar_can_create_student(self):
        registrar = self.env["res.users"].create(
            {
                "name": "Registrar User",
                "login": "registrar_user_sec",
                "group_ids": [
                    (6, 0, [self.env.ref("inom_university_core.group_univ_registrar").id])
                ],
            }
        )
        student = (
            self.env["univ.student"]
            .with_user(registrar)
            .create(
                {
                    "name": "Registrar Student",
                    "program_id": self.program.id,
                    "batch_id": self.batch.id,
                    "section_id": self.section.id,
                }
            )
        )
        self.assertTrue(student.id)
