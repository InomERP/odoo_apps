# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAcademics(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env["univ.program"].create({"name": "Test Program",
                                                       "code": "TP"})
        cls.semester = cls.env["univ.semester"].create({
            "name": "Sem 1", "code": "S1", "program_id": cls.program.id})
        cls.batch = cls.env["univ.batch"].create({
            "name": "2024", "code": "B24", "program_id": cls.program.id})
        cls.section = cls.env["univ.section"].create({
            "name": "A", "code": "A", "batch_id": cls.batch.id,
            "semester_id": cls.semester.id})
        cls.subject = cls.env["univ.subject"].create({
            "name": "Math", "code": "MATH", "program_id": cls.program.id,
            "semester_id": cls.semester.id, "credit_hours": 4.0})
        cls.faculty = cls.env["univ.faculty"].create({
            "name": "Dr X", "code": "FX"})
        cls.slot = cls.env["univ.timeslot"].create({
            "name": "P1", "start_time": 9.0, "end_time": 10.0})
        cls.room = cls.env["univ.room"].create({"name": "R1", "capacity": 30})

    def _make_session(self, **kw):
        vals = {
            "section_id": self.section.id, "subject_id": self.subject.id,
            "faculty_id": self.faculty.id, "slot_id": self.slot.id,
            "date": "2026-01-05",
        }
        vals.update(kw)
        return self.env["univ.timetable.session"].create(vals)

    def test_clash_detection_faculty(self):
        self._make_session()
        other_section = self.env["univ.section"].create({
            "name": "B", "code": "B", "batch_id": self.batch.id,
            "semester_id": self.semester.id})
        with self.assertRaises(ValidationError):
            self._make_session(section_id=other_section.id)

    def test_attendance_lock_blocks_edit(self):
        session = self._make_session()
        sheet = self.env["univ.attendance.sheet"].create(
            {"session_id": session.id})
        student = self.env["univ.student"].create({
            "name": "S1", "program_id": self.program.id,
            "batch_id": self.batch.id, "semester_id": self.semester.id,
            "section_id": self.section.id, "state": "active"})
        line = self.env["univ.attendance.line"].create({
            "sheet_id": sheet.id, "student_id": student.id, "state": "present"})
        sheet.state = "locked"
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            line.state = "absent"

    def test_grade_scale_gpa(self):
        scale = self.env["univ.grade.scale"]._get_default()
        if scale:
            label, point, is_pass = scale.grade_for_percent(95.0)
            self.assertTrue(is_pass)
            self.assertGreater(point, 0)

    def test_reevaluation_third_forced(self):
        schedule = self.env["univ.exam.schedule"].create({
            "exam_id": self.env["univ.exam"].create({
                "name": "E1",
                "exam_type_id": self.env["univ.exam.type"].create(
                    {"name": "Final", "category": "final"}).id,
                "program_id": self.program.id,
                "semester_id": self.semester.id}).id,
            "subject_id": self.subject.id, "date": "2026-01-10",
            "max_marks": 100})
        student = self.env["univ.student"].create({
            "name": "S2", "program_id": self.program.id,
            "batch_id": self.batch.id, "semester_id": self.semester.id,
            "section_id": self.section.id, "state": "active"})
        line = self.env["univ.exam.result.line"].create({
            "schedule_id": schedule.id, "student_id": student.id,
            "max_marks": 100, "obtained": 40})
        reeval = self.env["univ.exam.reevaluation"].create({
            "result_line_id": line.id, "evaluator2_marks": 55})
        self.assertTrue(reeval.needs_third)
