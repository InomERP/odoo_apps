"""Fee structure rules: totals, instalment split, publishing.

Run with:

    odoo -d <db> --test-enable --test-tags inom_fee --stop-after-init
"""
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import InomFeeCommon


@tagged('post_install', '-at_install', 'inom_fee')
class TestFeeStructure(InomFeeCommon):

    def test_total_is_sum_of_components(self):
        structure = self._make_structure(code='FT-TOT', publish=False)
        self.assertAlmostEqual(structure.total_amount, 100000.0)

    def test_instalments_must_total_100(self):
        with self.assertRaises(ValidationError):
            self._make_structure(code='FT-BAD', publish=False,
                                 instalments=(('Only', 90.0, 0),))

    def test_publish_requires_a_component(self):
        structure = self._make_structure(code='FT-EMPTY', publish=False,
                                         components=(), instalments=())
        with self.assertRaises(ValidationError):
            structure._inom_action_publish()

    def test_publish_sets_state(self):
        structure = self._make_structure(code='FT-PUB')
        self.assertEqual(structure.state, 'published')

    def test_negative_component_refused(self):
        with self.assertRaises(ValidationError):
            self._make_structure(code='FT-NEG', publish=False,
                                 components=(('Refund', -10.0),))

    def test_scholarship_value_checks(self):
        Scholarship = self.env['inom.scholarship']
        with self.assertRaises(ValidationError):
            Scholarship.create({'name': 'Zero', 'kind': 'amount', 'value': 0})
        with self.assertRaises(ValidationError):
            Scholarship.create({'name': 'Too much', 'kind': 'percent', 'value': 150})
