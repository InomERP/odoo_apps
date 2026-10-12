# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class UniversityCommon(TransactionCase):
    """Shared fixtures for University core tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.school = cls.env["univ.faculty_school"].create(
            {"name": "Test School", "code": "TS"}
        )
        cls.department = cls.env["univ.department"].create(
            {
                "name": "Test Department",
                "code": "TD",
                "faculty_school_id": cls.school.id,
            }
        )
        cls.program = cls.env["univ.program"].create(
            {
                "name": "Test Program",
                "code": "TP",
                "department_id": cls.department.id,
                "degree_type": "ug",
                "duration_years": 4.0,
                "total_semesters": 8,
            }
        )
        cls.batch = cls.env["univ.batch"].create(
            {
                "name": "Test Batch",
                "code": "TB",
                "program_id": cls.program.id,
                "start_year": 2024,
            }
        )
        cls.semester = cls.env["univ.semester"].create(
            {
                "name": "Semester 1",
                "code": "S1",
                "program_id": cls.program.id,
                "sequence": 1,
            }
        )
        cls.section = cls.env["univ.section"].create(
            {
                "name": "Section A",
                "code": "SA",
                "batch_id": cls.batch.id,
                "semester_id": cls.semester.id,
                "capacity": 60,
            }
        )

    @classmethod
    def _create_student(cls, name="Test Student", **kwargs):
        vals = {
            "name": name,
            "program_id": cls.program.id,
            "batch_id": cls.batch.id,
            "semester_id": cls.semester.id,
            "section_id": cls.section.id,
        }
        vals.update(kwargs)
        return cls.env["univ.student"].create(vals)
