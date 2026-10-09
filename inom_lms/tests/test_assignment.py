"""Assignments and submissions: dates, lateness, grading and the grader guard."""
from datetime import datetime, timedelta

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import InomLmsCommon


@tagged('post_install', '-at_install', 'inom_lms')
class TestAssignment(InomLmsCommon):

    def _submission(self, assignment, **vals):
        values = {'assignment_id': assignment.id, 'student_id': self.student.id}
        values.update(vals)
        return self.env['inom.submission'].create(values)

    def test_due_before_issue_refused(self):
        with self.assertRaises(ValidationError):
            assignment = self._assignment()
            assignment.write({'due_on': assignment.issued_on - timedelta(days=1)})

    def test_late_flag(self):
        assignment = self._assignment()
        on_time = self._submission(assignment)
        self.assertFalse(on_time.late)
        late_date = datetime.combine(assignment.due_on + timedelta(days=1),
                                     datetime.min.time())
        on_time.write({'submitted_on': late_date})
        self.assertTrue(on_time.late)

    def test_counts(self):
        assignment = self._assignment()
        submission = self._submission(assignment)
        self.assertEqual(assignment.submitted_count, 1)
        self.assertEqual(assignment.graded_count, 0)
        submission._inom_action_grade({'marks': 15, 'feedback': 'Good work.'})
        self.assertEqual(assignment.graded_count, 1)

    def test_grade_needs_mark_and_feedback(self):
        submission = self._submission(self._assignment())
        with self.assertRaises(ValidationError):
            submission._inom_action_grade({'feedback': 'No mark'})
        with self.assertRaises(ValidationError):
            submission._inom_action_grade({'marks': 10})
        self.assertEqual(submission._inom_action_grade(
            {'marks': 12, 'feedback': 'Fine.'}), {'state': 'graded'})
        self.assertEqual(submission.marks, 12.0)
        self.assertEqual(submission.state, 'graded')

    def test_marks_cannot_exceed_maximum(self):
        submission = self._submission(self._assignment())
        with self.assertRaises(ValidationError):
            submission._inom_action_grade({'marks': 25, 'feedback': 'Too many.'})

    def test_return_for_rework(self):
        submission = self._submission(self._assignment())
        self.assertEqual(submission._inom_action_return_for_rework(),
                         {'state': 'returned'})
        self.assertEqual(submission.state, 'returned')

    def test_one_submission_per_student(self):
        assignment = self._assignment()
        self._submission(assignment)
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), \
                self.cr.savepoint():
            self._submission(assignment)

    def test_non_grader_cannot_set_marks(self):
        submission = self._submission(self._assignment())
        user = new_test_user(self.env, login='lms_non_grader',
                             groups='base.group_user')
        with self.assertRaises(AccessError):
            submission.with_user(user).write({'marks': 20})
        self.assertFalse(submission.marks)

    def test_who_may_grade(self):
        Submission = self.env['inom.submission']
        plain = new_test_user(self.env, login='lms_plain', groups='base.group_user')
        faculty = new_test_user(self.env, login='lms_faculty',
                                groups='base.group_user,inom_base.group_inom_faculty')
        self.assertFalse(Submission.with_user(plain)._inom_may_grade())
        self.assertTrue(Submission.with_user(faculty)._inom_may_grade())
