# -*- coding: utf-8 -*-
from .common import UnivFeeCommon


class TestScholarship(UnivFeeCommon):

    def test_percent_award(self):
        scheme = self.env["univ.scholarship.scheme"].create({
            "name": "Merit",
            "amount_type": "percent",
            "amount": 10.0,
        })
        wrapper = self.env["univ.fee.invoice"].create({
            "student_id": self.student.id,
            "structure_id": self.structure.id,
        })
        # No move yet -> amount_total is 0; percent of 0 is 0
        self.assertEqual(scheme.compute_award_amount(wrapper), 0.0)

    def test_fixed_award(self):
        scheme = self.env["univ.scholarship.scheme"].create({
            "name": "Aid",
            "amount_type": "fixed",
            "amount": 5000.0,
        })
        award = self.env["univ.scholarship.award"].create({
            "scheme_id": scheme.id,
            "student_id": self.student.id,
            "amount": 5000.0,
        })
        award.action_submit()
        award.action_approve()
        self.assertEqual(award.state, "approved")
