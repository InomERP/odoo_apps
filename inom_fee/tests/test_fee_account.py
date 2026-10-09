"""Fee account amounts, schedule generation and state."""
from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import InomFeeCommon


@tagged('post_install', '-at_install', 'inom_fee')
class TestFeeAccount(InomFeeCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure = cls._make_structure(code='FT-ACC')
        # A student outside the enrolled state gets no automatic account, so
        # the account under test is built by hand.
        cls.student = cls._make_student(name='Manual Account Student', state='leave')

    def _account(self, **extra):
        vals = {'student_id': self.student.id, 'year_id': self.year.id,
                'structure_id': self.structure.id}
        vals.update(extra)
        return self.env['inom.fee.account'].create(vals)

    def test_amounts_without_scholarship(self):
        account = self._account()
        self.assertAlmostEqual(account.amount_gross, 100000.0)
        self.assertAlmostEqual(account.amount_discount, 0.0)
        self.assertAlmostEqual(account.amount_billed, 100000.0)
        self.assertEqual(account.state, 'draft')

    def test_percent_scholarship_discount(self):
        scholarship = self.env['inom.scholarship'].create(
            {'name': 'Merit 25', 'kind': 'percent', 'value': 25})
        account = self._account(scholarship_id=scholarship.id)
        self.assertAlmostEqual(account.amount_discount, 25000.0)
        self.assertAlmostEqual(account.amount_billed, 75000.0)

    def test_amount_scholarship_is_capped_at_gross(self):
        scholarship = self.env['inom.scholarship'].create(
            {'name': 'Huge', 'kind': 'amount', 'value': 999999})
        account = self._account(scholarship_id=scholarship.id)
        self.assertAlmostEqual(account.amount_billed, 0.0)

    def test_schedule_follows_instalment_template(self):
        account = self._account()
        result = account._inom_action_generate_schedule()
        self.assertEqual(result, {'lines': 2})
        lines = account.line_ids.sorted('due_date')
        self.assertEqual(lines.mapped('amount'), [40000.0, 60000.0])
        self.assertEqual(lines[0].due_date, self.year.date_start)
        self.assertEqual(lines.mapped('state'), ['pending', 'pending'])
        self.assertAlmostEqual(account.amount_due, 100000.0)

    def test_schedule_cannot_be_generated_twice(self):
        account = self._account()
        account._inom_action_generate_schedule()
        with self.assertRaises(ValidationError):
            account._inom_action_generate_schedule()

    def test_one_account_per_student_and_year(self):
        self._account()
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), \
                self.cr.savepoint():
            self._account()
