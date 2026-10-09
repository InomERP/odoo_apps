"""Enrolling a student raises their fee account and schedule."""
from odoo.tests import tagged

from .common import InomFeeCommon


@tagged('post_install', '-at_install', 'inom_fee')
class TestEnrolmentHook(InomFeeCommon):

    def _accounts(self, students):
        return self.env['inom.fee.account'].search(
            [('student_id', 'in', students.ids), ('year_id', '=', self.year.id)])

    def test_enrolled_student_gets_account_and_schedule(self):
        structure = self._make_structure(code='FT-HOOK')
        student = self._make_student()
        account = self._accounts(student)
        self.assertEqual(len(account), 1)
        self.assertEqual(account.structure_id, structure)
        self.assertEqual(len(account.line_ids), 2)

    def test_general_quota_structure_is_preferred(self):
        self._make_structure(code='FT-MGMT', quota='management')
        general = self._make_structure(code='FT-GEN2', quota='general')
        student = self._make_student()
        self.assertEqual(self._accounts(student).structure_id, general)

    def test_no_published_structure_does_not_block_enrolment(self):
        self._make_structure(code='FT-DRAFT', publish=False)
        student = self._make_student()
        self.assertEqual(student.state, 'enrolled')
        self.assertFalse(self._accounts(student))

    def test_batch_create_gives_each_student_one_account(self):
        self._make_structure(code='FT-BATCH')
        students = self.env['inom.student'].create([
            {'name': f'Batch Student {i}', 'programme_id': self.programme.id,
             'batch_id': self.batch.id, 'state': 'enrolled'}
            for i in range(5)
        ])
        accounts = self._accounts(students)
        self.assertEqual(len(accounts), 5)
        self.assertEqual(accounts.student_id, students)

    def test_moving_to_enrolled_creates_account_once(self):
        self._make_structure(code='FT-MOVE')
        student = self._make_student(state='leave')
        self.assertFalse(self._accounts(student))
        student.write({'state': 'enrolled'})
        self.assertEqual(len(self._accounts(student)), 1)
        # Writing enrolled again must not raise a second account.
        student.write({'state': 'enrolled'})
        self.assertEqual(len(self._accounts(student)), 1)

    def test_ensure_is_idempotent_on_a_recordset(self):
        self._make_structure(code='FT-IDEM')
        students = self._make_student(name='A') | self._make_student(name='B')
        self.assertFalse(students._inom_ensure_fee_account(),
                         'Students who already have an account got another one.')
        self.assertEqual(len(self._accounts(students)), 2)
