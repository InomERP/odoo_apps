"""Shared fixtures for the inom_lms tests.

Every test builds its own institution, department and course, so the suite
runs on an empty database as well as on one seeded with demo data.
"""
from datetime import date, timedelta

from odoo.tests import TransactionCase


class InomLmsCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.institution = env['inom.institution'].create({
            'name': 'LMS Test University', 'short_name': 'LTU', 'code': 'LTU-TEST'})
        cls.department = env['inom.department'].create({
            'name': 'LMS Test Department', 'code': 'LTDEP',
            'institution_id': cls.institution.id})
        cls.programme = env['inom.programme'].create({
            'name': 'LMS Test Programme', 'code': 'LTPROG',
            'department_id': cls.department.id})
        cls.course = env['inom.course'].create({
            'name': 'LMS Test Course', 'code': 'LT-101',
            'department_id': cls.department.id})
        cls.student = env['inom.student'].create({
            'name': 'LMS Test Student', 'programme_id': cls.programme.id})

    @classmethod
    def _lesson(cls, course=None, **vals):
        values = {'course_id': (course or cls.course).id, 'name': 'Lesson',
                  'content_type': 'link', 'url': 'https://example.com/page'}
        values.update(vals)
        return cls.env['inom.lesson'].create(values)

    @classmethod
    def _assignment(cls, **vals):
        today = date.today()
        values = {'name': 'Assignment', 'course_id': cls.course.id,
                  'issued_on': today, 'due_on': today + timedelta(days=7),
                  'max_marks': 20.0}
        values.update(vals)
        return cls.env['inom.assignment'].create(values)
