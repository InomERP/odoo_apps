# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from psycopg2 import IntegrityError
from odoo.tests.common import tagged
from odoo.tools import mute_logger
from .common import UniversityCommon


@tagged("post_install", "-at_install")
class TestDataIntegrity(UniversityCommon):

    @mute_logger("odoo.sql_db")
    def test_cannot_delete_program_with_students(self):
        self._create_student(name="Integrity Student")
        with self.assertRaises(IntegrityError):
            self.program.unlink()
            self.env.flush_all()

    def test_audit_log_is_immutable(self):
        log = self.env["univ.audit.log"].sudo().create(
            {
                "res_model": "univ.student",
                "res_id": 1,
                "res_name": "Test",
                "operation": "create",
            }
        )
        with self.assertRaises(UserError):
            log.write({"res_name": "Tampered"})

    @mute_logger("odoo.sql_db")
    def test_faculty_school_code_unique_per_company(self):
        with self.assertRaises(IntegrityError):
            self.env["univ.faculty_school"].create(
                {"name": "Dup School", "code": "TS"}
            )
            self.env.flush_all()

    def test_section_capacity_positive(self):
        with self.assertRaises(Exception):
            self.env["univ.section"].create(
                {
                    "name": "Bad Section",
                    "code": "BS",
                    "batch_id": self.batch.id,
                    "semester_id": self.semester.id,
                    "capacity": -5,
                }
            )
